from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import pandas as pd
from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.config import settings
from app.core.errors import CHART_GENERATION_FAILED, DATASET_NOT_READY, LLM_UPSTREAM, AppError
from app.models import Dataset, DatasetColumn
from app.services import dataset_parse, storage
from app.services.chart_spec_validate import validate_chart_spec
from app.services.data_analysis import compute_column_stats, execute_analysis_plan

_log = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_LLM_RETRIES = 1

_openrouter_client: AsyncOpenAI | None = None
_openai_client: AsyncOpenAI | None = None


def _friendly_upstream_message(exc: Exception) -> str:
    """Short, user-facing message. Log the full exception separately."""
    if isinstance(exc, RateLimitError):
        return (
            "Too many chart requests right now. Please wait a minute and try again."
        )
    if isinstance(exc, APITimeoutError):
        return "The chart request timed out. Please try again."

    status = getattr(exc, "status_code", None)
    if status == 429:
        return (
            "The chart service is temporarily busy. Please wait a moment and try again."
        )
    if status in (401, 403):
        return (
            "Chart generation could not be authorized. Check API settings on the server."
        )
    if status in (502, 503):
        return (
            "The chart service is temporarily unavailable. Please try again shortly."
        )

    text = str(exc).lower()
    if "429" in text or "rate-limited" in text or (
        "rate" in text and "limit" in text
    ):
        return (
            "The chart service is temporarily busy. Please wait a moment and try again."
        )
    if "timeout" in text or "timed out" in text:
        return "The chart request timed out. Please try again."

    return (
        "We couldn’t generate the chart right now. Please try again in a moment."
    )


def _get_openrouter_client() -> AsyncOpenAI:
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=_OPENROUTER_BASE_URL,
            timeout=settings.llm_chart_timeout_seconds,
        )
    return _openrouter_client


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        key = settings.openai_api_key
        if not key or not str(key).strip():
            raise RuntimeError("OpenAI API key not configured for fallback")
        kwargs: dict[str, Any] = {
            "api_key": str(key).strip(),
            "timeout": settings.llm_chart_timeout_seconds,
        }
        if settings.openai_base_url and str(settings.openai_base_url).strip():
            kwargs["base_url"] = str(settings.openai_base_url).strip()
        _openai_client = AsyncOpenAI(**kwargs)
    return _openai_client


def _openai_fallback_available() -> bool:
    k = settings.openai_api_key
    return bool(k and str(k).strip())


# ---------------------------------------------------------------------------
# Phase 1 prompt: column stats + user question → structured analysis plan
# ---------------------------------------------------------------------------
_PLANNER_PROMPT = """\
You are a data-analysis planner. Given column metadata and a user question, output ONLY a JSON object describing how to query the dataset.

JSON schema (all keys required):
{"chart_type":"bar|line|pie|stacked_bar","x_field":"col","y_field":"col","series_field":"col or null","transforms":[],"group_by":["col",...],"aggregation":{"column":"col","function":"sum|mean|count|min|max|median"},"filters":[],"sort":{"by":"col","order":"asc|desc"} or null,"limit":int,"normalize":false}

TRANSFORMS — derive new columns BEFORE grouping. Array of objects, each with "type" plus type-specific keys:
- threshold: split numeric col at a value. {"type":"threshold","column":"col","value":"median|mean|q25|q75|<number>","output":"new_col","labels":["Below median","Above median"]}
- bin: bucket numeric col. {"type":"bin","column":"col","output":"new_col","bins":5} or {"type":"bin","column":"col","output":"new_col","edges":[0,10,20,50,100],"labels":["0-10","10-20","20-50","50-100"]}
- date_part: extract year/month/quarter/weekday/hour/year_month from date/string col. {"type":"date_part","column":"col","part":"year|month|month_name|quarter|day|weekday|hour|year_month","output":"new_col"}
- math: arithmetic between two cols or col and constant. {"type":"math","column_a":"col","column_b":"col","operation":"add|subtract|multiply|divide","output":"new_col"} or {"type":"math","column_a":"col","constant":100,"operation":"multiply","output":"new_col"}
- top_n: keep top N values by frequency or another col, rest become "Other". {"type":"top_n","column":"col","n":10,"by":"value_col","agg":"sum"}
- percentile: split into quantile groups. {"type":"percentile","column":"col","output":"new_col","groups":4,"labels":["Q1","Q2","Q3","Q4"]}
- ratio: divide numerator by denominator col. {"type":"ratio","numerator":"col","denominator":"col","output":"new_col","as_percentage":true}

After transforms, the output column name can be used in x_field, y_field, series_field, group_by, aggregation, and filters.

NORMALIZE: set true to convert aggregated values to percentages of total.

Rules:
- pie: only for share/percentage/parts-of-whole. line: temporal x or trend. stacked_bar: two categorical dims. bar: default.
- group_by must contain x_field (and series_field for stacked_bar).
- aggregation.column = y_field. For count, any column works.
- Column names must match metadata exactly (transform output names are your choice).
- sort.by = aggregated y_field usually. desc for bar, asc for line.
- limit: 10-50 for bar/pie, up to 100 for line/stacked_bar.
- For in/not_in filter ops, value must be a JSON array.
- USE transforms when the user asks about above/below median, binned ranges, date breakdowns, ratios, top-N grouping, percentiles, or computed columns. This is critical — do not skip transforms when they are needed.
Output ONLY the JSON object."""


# ---------------------------------------------------------------------------
# Phase 2 prompt: aggregated data + user question → chart_spec
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are Chat2Chart. Turn a user request plus aggregated data rows into exactly one JSON object. No markdown, no fences, no extra text.

Output shape:
{"assistant_message":"short friendly explanation","chart_spec":{...}}

The data rows provided are ALREADY aggregated from the full dataset — use them as-is. Do NOT re-aggregate, invent, or modify values.

chart_spec schema (v1):
{"version":1,"type":"bar|line|pie|stacked_bar","title":"str","subtitle":"str|null","encoding":{"x":{"field":"col","label":"display","type":"category|quantitative|temporal"},"y":{...},"series":{...stacked_bar only},"label":{...pie only},"value":{...pie only}},"data":{"rows":[...max 100]},"style":{"palette":["#hex",...]} optional}

Encoding rules:
- bar/line: only x and y
- stacked_bar: x, series, y
- pie: label and value (or x and y)
- Column names in encoding and rows must match the provided data exactly.
Output ONLY the JSON object."""


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("Expecting '{'", text, 0)
    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(text, start)
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object")
    return obj


async def _llm_call_single_provider(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """One provider + model. Raises AppError LLM_UPSTREAM on API failures; CHART_* on parse/content."""
    last_error: Exception | None = None
    for attempt in range(_MAX_LLM_RETRIES + 1):
        try:
            completion = await client.chat.completions.create(
                model=model,
                temperature=0.1,
                messages=messages,
            )
        except (APITimeoutError, RateLimitError, APIError) as e:
            _log.warning("Chart upstream API error: %s", e, exc_info=True)
            raise AppError(
                502, LLM_UPSTREAM,
                _friendly_upstream_message(e),
                details={"type": type(e).__name__},
            ) from e
        except Exception as e:
            _log.warning("Chart upstream error: %s", e, exc_info=True)
            raise AppError(
                502, LLM_UPSTREAM, _friendly_upstream_message(e),
            ) from e

        if completion is None:
            if attempt < _MAX_LLM_RETRIES:
                _log.warning("Null completion attempt %d, retrying…", attempt + 1)
                continue
            raise AppError(502, LLM_UPSTREAM, "Model returned no completion object.")

        choices = completion.choices
        if not choices:
            if attempt < _MAX_LLM_RETRIES:
                _log.warning("Empty choices attempt %d, retrying…", attempt + 1)
                continue
            raise AppError(502, LLM_UPSTREAM, "Model returned no choices.")

        first = choices[0]
        if first is None or first.message is None:
            if attempt < _MAX_LLM_RETRIES:
                _log.warning("Missing message attempt %d, retrying…", attempt + 1)
                continue
            raise AppError(502, LLM_UPSTREAM, "Model returned an incomplete choice.")

        choice = first.message.content
        if not choice or not choice.strip():
            if attempt < _MAX_LLM_RETRIES:
                _log.warning("Empty response attempt %d, retrying…", attempt + 1)
                continue
            raise AppError(422, CHART_GENERATION_FAILED, "Model returned an empty response.")

        try:
            parsed = _parse_json_object(choice)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < _MAX_LLM_RETRIES:
                _log.warning("JSON parse failed attempt %d, retrying… (%s)", attempt + 1, e)
                continue
            raise AppError(
                422,
                CHART_GENERATION_FAILED,
                "The chart response could not be read. Try again or rephrase your question.",
            ) from e

        if isinstance(parsed, dict):
            return parsed

        if attempt < _MAX_LLM_RETRIES:
            _log.warning("Non-object response attempt %d, retrying…", attempt + 1)
            continue
        raise AppError(422, CHART_GENERATION_FAILED, "Model response must be a JSON object.")

    raise AppError(
        422,
        CHART_GENERATION_FAILED,
        "The chart response could not be read. Try again or rephrase your question.",
    )


async def _llm_call(system: str, user_content: str) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    chain: list[tuple[AsyncOpenAI, str, str]] = [
        (_get_openrouter_client(), settings.openrouter_model, "openrouter"),
    ]
    if _openai_fallback_available():
        chain.append((_get_openai_client(), settings.openai_model, "openai"))

    for idx, (client, model, label) in enumerate(chain):
        try:
            return await _llm_call_single_provider(client, model, messages)
        except AppError as err:
            if err.code != LLM_UPSTREAM:
                raise
            if idx == len(chain) - 1:
                raise
            _log.warning(
                "Chart LLM %s failed (%s); retrying with OpenAI",
                label,
                err.message,
            )

    raise AssertionError("LLM provider chain exhausted without result")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def build_chart_spec_llm(
    dataset: Dataset,
    columns: list[DatasetColumn],
    user_message: str,
) -> tuple[dict[str, Any], str]:
    if dataset.status != "ready":
        raise AppError(422, DATASET_NOT_READY, "Dataset is not ready yet.")
    if not columns:
        raise AppError(422, CHART_GENERATION_FAILED, "Dataset has no column metadata.")

    try:
        raw_bytes = await storage.get_dataset_object(dataset.storage_key)
    except Exception as e:
        raise AppError(
            422, CHART_GENERATION_FAILED, f"Could not read dataset file: {e}",
        ) from e

    def _load_full_df() -> pd.DataFrame:
        return dataset_parse.read_tabular(raw_bytes, dataset.original_filename)

    try:
        df = await asyncio.to_thread(_load_full_df)
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            422, CHART_GENERATION_FAILED, f"Could not load dataset: {e}",
        ) from e

    def _build_stats() -> str:
        stats = compute_column_stats(df)
        return json.dumps({"total_rows": len(df), "columns": stats}, ensure_ascii=False)

    try:
        stats_json = await asyncio.to_thread(_build_stats)
    except Exception as e:
        raise AppError(
            422, CHART_GENERATION_FAILED, f"Could not compute column stats: {e}",
        ) from e

    # --- Phase 1: Planner ---------------------------------------------------
    planner_user = (
        f"Dataset statistics:\n{stats_json}\n\n"
        f"User request:\n{user_message.strip() or '(empty)'}\n"
    )
    plan = await _llm_call(_PLANNER_PROMPT, planner_user)
    _log.info("Analysis plan: %s", json.dumps(plan, default=str)[:500])

    # --- Execute plan on full DataFrame -------------------------------------
    def _run_plan() -> list[dict[str, Any]]:
        return execute_analysis_plan(df, plan)

    try:
        result_rows = await asyncio.to_thread(_run_plan)
    except Exception as e:
        _log.error("Plan execution failed: %s", e, exc_info=True)
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            "We couldn’t run that analysis on your data. Try rephrasing your question.",
        ) from e

    if not result_rows:
        raise AppError(
            422, CHART_GENERATION_FAILED,
            "The query returned no data. Try a different question or filter.",
        )

    # --- Phase 2: Chart spec from aggregated data ---------------------------
    result_json = json.dumps(
        {"rows": result_rows, "total_source_rows": len(df)},
        ensure_ascii=False,
    )

    chart_user = (
        f"Dataset columns (from aggregated result):\n"
        f"{json.dumps(list(result_rows[0].keys()), ensure_ascii=False)}\n\n"
        f"Aggregated data (computed from ALL {len(df)} rows):\n"
        f"{result_json}\n\n"
        f"User request:\n{user_message.strip() or '(empty)'}\n"
    )
    parsed = await _llm_call(_SYSTEM_PROMPT, chart_user)

    assistant_message = parsed.get("assistant_message")
    chart_spec = parsed.get("chart_spec")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise AppError(422, CHART_GENERATION_FAILED, "Model response missing assistant_message.")
    if not isinstance(chart_spec, dict):
        raise AppError(422, CHART_GENERATION_FAILED, "Model response missing chart_spec.")

    chart_spec.setdefault("version", 1)
    validate_chart_spec(chart_spec)
    return chart_spec, assistant_message.strip()[:4000]
