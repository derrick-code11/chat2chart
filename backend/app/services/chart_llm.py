from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.config import settings
from app.core.errors import CHART_GENERATION_FAILED, DATASET_NOT_READY, LLM_UPSTREAM, AppError
from app.models import Dataset, DatasetColumn
from app.services import dataset_parse, storage
from app.services.chart_spec_validate import validate_chart_spec


_SYSTEM_PROMPT = """You are Chat2Chart, a data visualization expert. You turn a natural-language request plus a small tabular preview into one JSON object. No markdown, no code fences, no text before or after the JSON.

Output shape (exactly two keys):
- "assistant_message": short, friendly, user-facing (one or two sentences max).
- "chart_spec": version 1 spec described below.

Before you write JSON, reason silently: intent (compare, trend, share, breakdown), exact column names from the preview, chart type, which fields map to encoding slots, and rows (≤100).

Chart types and encoding (backend rules):
- "bar" and "line": ONLY encoding "x" and "y". Each row must contain the x field, y field, and nothing else is used for plotting—so one numeric or category y per x position. Use for simple two-column stories or one row per bar/point.
- "stacked_bar": encoding "x", "series", and "y". Each row must include all three fields. Use when comparing a measure across two categorical dimensions (e.g. quarter × region).
- "pie": encoding "label" and "value", OR encoding "x" and "y" (same meaning as label/value). Each row: those two fields.

chart_spec schema:
- "version": 1
- "type": "bar" | "line" | "pie" | "stacked_bar"
- "title": string (specific and clear), "subtitle": string or null
- "encoding": objects with "field" (exact column name), "label" (display), "type": "category" | "quantitative" | "temporal" as appropriate
- "data": { "rows": [ ... ] } — objects whose keys are exactly the field names referenced in encoding; max 100 rows; aggregate or filter if needed
- "style": optional object, e.g. { "palette": ["#2563eb", "#7c3aed"] } (2–6 hex colors), or omit

Golden rules:
- Column names in encoding and rows must match the dataset preview character-for-character.
- Do not invent values; stay consistent with the preview. If data is thin, still chart what exists and briefly note the limitation in assistant_message.
- Prefer "bar" for simple comparisons; "line" for time-like x when the request implies a trend; "pie" for parts-of-a-whole; "stacked_bar" when you need category × series × measure.

Examples (patterns only; your real answer must use the actual preview columns and rows provided in the user message).

Example A — simple bar (two columns, one measure per category):
{"assistant_message":"Here is a bar chart of sales by product.","chart_spec":{"version":1,"type":"bar","title":"Sales by Product","subtitle":null,"encoding":{"x":{"field":"Product","label":"Product","type":"category"},"y":{"field":"Sales","label":"Sales","type":"quantitative"}},"data":{"rows":[{"Product":"A","Sales":120},{"Product":"B","Sales":90}]},"style":{"palette":["#2563eb","#7c3aed"]}}}

Example B — stacked bar (quarter × region × revenue; use stacked_bar, not bar, so all three columns matter):
{"assistant_message":"Stacked bars show revenue by quarter, split by region.","chart_spec":{"version":1,"type":"stacked_bar","title":"Revenue by Quarter and Region","subtitle":null,"encoding":{"x":{"field":"Quarter","label":"Quarter","type":"category"},"series":{"field":"Region","label":"Region","type":"category"},"y":{"field":"Revenue","label":"Revenue","type":"quantitative"}},"data":{"rows":[{"Quarter":"Q1","Region":"North","Revenue":45000},{"Quarter":"Q1","Region":"South","Revenue":32000},{"Quarter":"Q2","Region":"North","Revenue":51000},{"Quarter":"Q2","Region":"South","Revenue":38000}]},"style":{"palette":["#2563eb","#7c3aed","#0d9488"]}}}

Example C — pie:
{"assistant_message":"Pie chart of sales share by product.","chart_spec":{"version":1,"type":"pie","title":"Sales Share","subtitle":null,"encoding":{"label":{"field":"Product","label":"Product","type":"category"},"value":{"field":"Sales","label":"Sales","type":"quantitative"}},"data":{"rows":[{"Product":"Laptop","Sales":42000},{"Product":"Phone","Sales":31000},{"Product":"Tablet","Sales":18000}]},"style":{"palette":["#2563eb","#7c3aed","#f59e0b"]}}}

Output only the JSON object for the real user request and preview in the next message."""


def _column_summaries(columns: list[DatasetColumn]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in columns:
        out.append(
            {
                "name": c.name,
                "inferred_type": c.inferred_type,
                "sample_values": c.sample_values,
            }
        )
    return out


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def _build_preview_payload(
    data: bytes,
    dataset: Dataset,
    columns: list[DatasetColumn],
    max_rows: int,
) -> tuple[str, str]:
    df = dataset_parse.read_tabular_head(data, dataset.original_filename, max_rows)
    rows, truncated = dataset_parse.preview_records(df, max_rows)
    col_json = json.dumps(_column_summaries(columns), ensure_ascii=False, indent=2)
    rows_json = json.dumps(
        {"rows": rows, "truncated": truncated},
        ensure_ascii=False,
        indent=2,
    )
    return col_json, rows_json


async def build_chart_spec_llm(
    dataset: Dataset,
    columns: list[DatasetColumn],
    user_message: str,
) -> tuple[dict[str, Any], str]:
    if dataset.status != "ready":
        raise AppError(422, DATASET_NOT_READY, "Dataset is not ready yet.")
    if not columns:
        raise AppError(422, CHART_GENERATION_FAILED, "Dataset has no column metadata.")

    max_rows = min(settings.dataset_preview_max_rows, 100)

    try:
        data = await storage.get_dataset_object(dataset.storage_key)
    except Exception as e:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"Could not read dataset file: {e}",
        ) from e

    def _sync_preview() -> tuple[str, str]:
        return _build_preview_payload(data, dataset, columns, max_rows)

    try:
        col_json, rows_json = await asyncio.to_thread(_sync_preview)
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"Could not load dataset preview: {e}",
        ) from e

    user_prompt = (
        f"Dataset columns (JSON):\n{col_json}\n\n"
        f"Preview rows (JSON):\n{rows_json}\n\n"
        f"User request:\n{user_message.strip() or '(empty)'}\n"
    )

    client_kwargs: dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "timeout": settings.llm_chart_timeout_seconds,
    }
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url
    client = AsyncOpenAI(**client_kwargs)

    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except (APITimeoutError, RateLimitError, APIError) as e:
        raise AppError(
            502,
            LLM_UPSTREAM,
            f"Chart model request failed: {e}",
            details={"type": type(e).__name__},
        ) from e
    except Exception as e:
        raise AppError(
            502,
            LLM_UPSTREAM,
            f"Chart model request failed: {e}",
        ) from e

    choice = completion.choices[0].message.content
    if not choice or not choice.strip():
        raise AppError(422, CHART_GENERATION_FAILED, "Model returned an empty response.")

    try:
        parsed = _parse_json_object(choice)
    except (json.JSONDecodeError, ValueError) as e:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"Model did not return valid JSON: {e}",
        ) from e

    if not isinstance(parsed, dict):
        raise AppError(422, CHART_GENERATION_FAILED, "Model response must be a JSON object.")

    assistant_message = parsed.get("assistant_message")
    chart_spec = parsed.get("chart_spec")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise AppError(422, CHART_GENERATION_FAILED, "Model response missing assistant_message.")
    if not isinstance(chart_spec, dict):
        raise AppError(422, CHART_GENERATION_FAILED, "Model response missing chart_spec.")

    chart_spec.setdefault("version", 1)
    validate_chart_spec(chart_spec)
    return chart_spec, assistant_message.strip()[:4000]
