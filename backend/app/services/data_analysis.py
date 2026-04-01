"""Execute structured analysis plans on full DataFrames.

An analysis plan is a JSON dict produced by the LLM planner.  This module
validates each field, runs the corresponding pandas operations, and returns
a small result table (≤ ``max_rows`` rows) ready for the chart-spec prompt.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.services.dataset_parse import json_safe_scalar

_log = logging.getLogger(__name__)

_MAX_RESULT_ROWS = 100
_ALLOWED_AGG_FUNCS = frozenset({"sum", "mean", "count", "min", "max", "median"})
_ALLOWED_FILTER_OPS = frozenset({"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "contains"})
_ALLOWED_SORT_ORDERS = frozenset({"asc", "desc"})
_ALLOWED_TRANSFORM_TYPES = frozenset({
    "threshold", "bin", "date_part", "math", "top_n", "percentile", "ratio",
})


def compute_column_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return rich per-column metadata so the LLM planner can choose
    groupings, filters, and aggregations without seeing raw rows."""
    stats: list[dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        info: dict[str, Any] = {
            "name": str(col),
            "dtype": str(s.dtype),
            "non_null_count": int(s.notna().sum()),
            "null_count": int(s.isna().sum()),
            "n_unique": int(s.nunique()),
        }

        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            info["type"] = "numeric"
            info["min"] = json_safe_scalar(desc.get("min"))
            info["max"] = json_safe_scalar(desc.get("max"))
            info["mean"] = json_safe_scalar(desc.get("mean"))
            info["median"] = json_safe_scalar(s.median())
            info["std"] = json_safe_scalar(desc.get("std"))
            q = s.quantile([0.25, 0.75]).to_dict()
            info["q25"] = json_safe_scalar(q.get(0.25))
            info["q75"] = json_safe_scalar(q.get(0.75))
        elif pd.api.types.is_datetime64_any_dtype(s):
            info["type"] = "datetime"
            info["min"] = json_safe_scalar(s.min())
            info["max"] = json_safe_scalar(s.max())
        else:
            info["type"] = "categorical"
            top_values = s.value_counts().head(15)
            info["top_values"] = [
                {"value": json_safe_scalar(v), "count": int(c)}
                for v, c in top_values.items()
            ]

        stats.append(info)

    return stats


# ---------------------------------------------------------------------------
# Transforms: derive new columns before filtering/grouping
# ---------------------------------------------------------------------------

def _apply_transforms(df: pd.DataFrame, transforms: list[dict]) -> pd.DataFrame:
    df = df.copy()
    for t in transforms:
        ttype = t.get("type")
        if ttype not in _ALLOWED_TRANSFORM_TYPES:
            _log.warning("Unknown transform type %r, skipping", ttype)
            continue
        try:
            if ttype == "threshold":
                df = _transform_threshold(df, t)
            elif ttype == "bin":
                df = _transform_bin(df, t)
            elif ttype == "date_part":
                df = _transform_date_part(df, t)
            elif ttype == "math":
                df = _transform_math(df, t)
            elif ttype == "top_n":
                df = _transform_top_n(df, t)
            elif ttype == "percentile":
                df = _transform_percentile(df, t)
            elif ttype == "ratio":
                df = _transform_ratio(df, t)
        except Exception as e:
            _log.warning("Transform %r failed: %s", ttype, e)
    return df


def _transform_threshold(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Split a numeric column into two categories based on a threshold.
    Supports literal values or "median", "mean", "q25", "q75"."""
    col = t["column"]
    output = t.get("output", f"{col}_group")
    value = t.get("value", "median")
    labels = t.get("labels", ["Below", "Above"])

    if col not in df.columns:
        _log.warning("Threshold column %r not found", col)
        return df

    s = pd.to_numeric(df[col], errors="coerce")
    if isinstance(value, str):
        stat_funcs = {"median": s.median, "mean": s.mean, "q25": lambda: s.quantile(0.25), "q75": lambda: s.quantile(0.75)}
        func = stat_funcs.get(value)
        if func:
            value = func()
        else:
            value = float(value)

    lo = labels[0] if len(labels) > 0 else "Below"
    hi = labels[1] if len(labels) > 1 else "Above"
    df[output] = np.where(s >= value, hi, lo)
    df.loc[s.isna(), output] = None
    return df


def _transform_bin(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Bin a numeric column into equal-width or custom bins."""
    col = t["column"]
    output = t.get("output", f"{col}_bin")
    n_bins = t.get("bins", 5)
    custom_edges = t.get("edges")
    custom_labels = t.get("labels")

    if col not in df.columns:
        return df

    s = pd.to_numeric(df[col], errors="coerce")
    if custom_edges:
        edges = [float(e) for e in custom_edges]
        lbls = custom_labels if custom_labels and len(custom_labels) == len(edges) - 1 else None
        df[output] = pd.cut(s, bins=edges, labels=lbls, include_lowest=True).astype(str)
    else:
        df[output] = pd.cut(s, bins=int(n_bins), include_lowest=True).astype(str)
    df.loc[s.isna(), output] = None
    return df


def _transform_date_part(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Extract a date part (year, month, quarter, day, weekday, hour) from a column."""
    col = t["column"]
    part = t.get("part", "month")
    output = t.get("output", f"{col}_{part}")

    if col not in df.columns:
        return df

    dt = pd.to_datetime(df[col], errors="coerce")
    extractors = {
        "year": lambda d: d.dt.year,
        "month": lambda d: d.dt.month,
        "month_name": lambda d: d.dt.month_name(),
        "quarter": lambda d: d.dt.quarter.map(lambda q: f"Q{q}"),
        "day": lambda d: d.dt.day,
        "weekday": lambda d: d.dt.day_name(),
        "hour": lambda d: d.dt.hour,
        "year_month": lambda d: d.dt.to_period("M").astype(str),
    }
    fn = extractors.get(part)
    if fn:
        df[output] = fn(dt)
    else:
        _log.warning("Unknown date part %r", part)
    return df


def _transform_math(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Create a column from simple arithmetic between two columns or a column and a constant.
    Operations: add, subtract, multiply, divide."""
    col_a = t.get("column_a") or t.get("column")
    col_b = t.get("column_b")
    constant = t.get("constant")
    op = t.get("operation", "divide")
    output = t.get("output", "calculated")

    if col_a not in df.columns:
        return df

    a = pd.to_numeric(df[col_a], errors="coerce")
    if col_b and col_b in df.columns:
        b = pd.to_numeric(df[col_b], errors="coerce")
    elif constant is not None:
        b = float(constant)
    else:
        return df

    ops = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: a / b.replace(0, np.nan) if isinstance(b, pd.Series) else a / (b if b != 0 else np.nan),
    }
    fn = ops.get(op)
    if fn:
        df[output] = fn()
    return df


def _transform_top_n(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Keep only top N values of a column by another column, group rest as 'Other'."""
    col = t["column"]
    by = t.get("by", col)
    n = t.get("n", 10)
    output = t.get("output", col)
    agg = t.get("agg", "sum")

    if col not in df.columns:
        return df

    if by in df.columns and pd.api.types.is_numeric_dtype(df[by]):
        top = df.groupby(col, dropna=False)[by].agg(agg).nlargest(int(n)).index
    else:
        top = df[col].value_counts().head(int(n)).index

    if output == col:
        df[col] = df[col].where(df[col].isin(top), other="Other")
    else:
        df[output] = df[col].where(df[col].isin(top), other="Other")
    return df


def _transform_percentile(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Assign each row to a percentile group (quartile, decile, etc.)."""
    col = t["column"]
    output = t.get("output", f"{col}_percentile")
    q = t.get("groups", 4)
    labels = t.get("labels")

    if col not in df.columns:
        return df

    s = pd.to_numeric(df[col], errors="coerce")
    if labels and len(labels) == int(q):
        df[output] = pd.qcut(s, q=int(q), labels=labels, duplicates="drop").astype(str)
    else:
        df[output] = pd.qcut(s, q=int(q), duplicates="drop").astype(str)
    df.loc[s.isna(), output] = None
    return df


def _transform_ratio(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Compute ratio of numerator column to denominator column, optionally as percentage."""
    num = t.get("numerator")
    den = t.get("denominator")
    output = t.get("output", "ratio")
    as_pct = t.get("as_percentage", False)

    if not num or not den or num not in df.columns or den not in df.columns:
        return df

    n = pd.to_numeric(df[num], errors="coerce")
    d = pd.to_numeric(df[den], errors="coerce").replace(0, np.nan)
    df[output] = n / d
    if as_pct:
        df[output] = (df[output] * 100).round(2)
    return df


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def _apply_filters(df: pd.DataFrame, filters: list[dict]) -> pd.DataFrame:
    for f in filters:
        col = f.get("column")
        op = f.get("op", "eq")
        val = f.get("value")
        if col not in df.columns:
            _log.warning("Filter column %r not in DataFrame, skipping", col)
            continue
        if op not in _ALLOWED_FILTER_OPS:
            _log.warning("Unknown filter op %r, skipping", op)
            continue

        s = df[col]
        if op == "eq":
            df = df[s == val]
        elif op == "neq":
            df = df[s != val]
        elif op == "gt":
            df = df[s > val]
        elif op == "gte":
            df = df[s >= val]
        elif op == "lt":
            df = df[s < val]
        elif op == "lte":
            df = df[s <= val]
        elif op == "in":
            df = df[s.isin(val if isinstance(val, list) else [val])]
        elif op == "not_in":
            df = df[~s.isin(val if isinstance(val, list) else [val])]
        elif op == "contains":
            df = df[s.astype(str).str.contains(str(val), case=False, na=False)]

    return df


def _execute_single_agg(
    df: pd.DataFrame,
    valid_group_by: list[str],
    agg_col: str | None,
    agg_func: str,
    normalize: bool,
    plan: dict[str, Any],
) -> pd.DataFrame:
    if valid_group_by:
        if agg_func == "count":
            count_name = agg_col if (agg_col and agg_col not in valid_group_by) else "count"
            result = (
                df.groupby(valid_group_by, dropna=False)
                .size()
                .reset_index(name=count_name)
            )
            if normalize:
                total = result[count_name].sum()
                if total > 0:
                    result[count_name] = (result[count_name] / total * 100).round(2)
        elif agg_col and agg_col in df.columns:
            if agg_col in valid_group_by:
                agg_label = f"{agg_col}_{agg_func}"
                result = (
                    df.groupby(valid_group_by, dropna=False)[agg_col]
                    .agg(agg_func)
                    .reset_index(name=agg_label)
                )
            else:
                result = (
                    df.groupby(valid_group_by, dropna=False)[agg_col]
                    .agg(agg_func)
                    .reset_index()
                )
            if normalize:
                target_col = agg_label if agg_col in valid_group_by else agg_col
                total = result[target_col].sum()
                if total > 0:
                    result[target_col] = (result[target_col] / total * 100).round(2)
        else:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            target = numeric_cols[0] if numeric_cols else df.columns[0]
            result = (
                df.groupby(valid_group_by, dropna=False)[target]
                .agg(agg_func)
                .reset_index()
            )
    elif agg_col and agg_col in df.columns:
        x_col = plan.get("x_field")
        if x_col and x_col in df.columns:
            result = df[[x_col, agg_col]].copy()
        else:
            result = df[[agg_col]].copy()
    else:
        result = df.copy()
    return result


def _execute_multi_agg(
    df: pd.DataFrame,
    valid_group_by: list[str],
    aggs: list[dict],
    normalize: bool,
) -> pd.DataFrame:
    """Apply multiple aggregations to the same group-by, producing one column per agg."""
    agg_dict: dict[str, tuple[str, str]] = {}
    rename_map: dict[str, str] = {}

    for i, a in enumerate(aggs):
        col = a.get("column")
        func = a.get("function", "count")
        out = a.get("output", f"{col}_{func}")

        if func not in _ALLOWED_AGG_FUNCS:
            continue
        if func == "count":
            tmp_name = f"_count_{i}"
            agg_dict[tmp_name] = (col or valid_group_by[0], "count")
            rename_map[tmp_name] = out
        elif col and col in df.columns:
            tmp_name = f"_agg_{i}"
            agg_dict[tmp_name] = (col, func)
            rename_map[tmp_name] = out

    if not agg_dict:
        return df.groupby(valid_group_by, dropna=False).size().reset_index(name="count")

    grouped = df.groupby(valid_group_by, dropna=False)
    result = grouped.agg(**agg_dict).reset_index()
    result = result.rename(columns=rename_map)

    if normalize:
        for out_col in rename_map.values():
            if out_col in result.columns:
                total = result[out_col].sum()
                if total > 0:
                    result[out_col] = (result[out_col] / total * 100).round(2)

    return result


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def execute_analysis_plan(
    df: pd.DataFrame,
    plan: dict[str, Any],
    max_rows: int = _MAX_RESULT_ROWS,
) -> list[dict[str, Any]]:
    """Execute a validated analysis plan and return JSON-safe row dicts."""

    # 1. Transforms: derive new columns first
    if plan.get("transforms"):
        df = _apply_transforms(df, plan["transforms"])

    # 2. Filters
    if plan.get("filters"):
        df = _apply_filters(df, plan["filters"])

    # 3. Group-by & aggregation
    group_by = plan.get("group_by") or []
    valid_group_by = [c for c in group_by if c in df.columns]
    normalize = plan.get("normalize", False)

    # Support multi-aggregation via "aggregations" (array) or single "aggregation" (dict)
    multi_aggs = plan.get("aggregations")
    if multi_aggs and isinstance(multi_aggs, list) and valid_group_by:
        result = _execute_multi_agg(df, valid_group_by, multi_aggs, normalize)
    else:
        agg_raw = plan.get("aggregation") or {}
        agg_col = agg_raw.get("column")
        agg_func = agg_raw.get("function", "count")

        if agg_func not in _ALLOWED_AGG_FUNCS:
            _log.warning("Unknown agg function %r, falling back to count", agg_func)
            agg_func = "count"

        result = _execute_single_agg(df, valid_group_by, agg_col, agg_func, normalize, plan)

    # 4. Sort
    sort_spec = plan.get("sort")
    if sort_spec and isinstance(sort_spec, dict):
        sort_col = sort_spec.get("by")
        sort_order = sort_spec.get("order", "desc")
        if sort_col and sort_col in result.columns:
            result = result.sort_values(
                sort_col, ascending=(sort_order == "asc")
            )

    # 5. Limit
    limit = plan.get("limit", max_rows)
    if not isinstance(limit, int) or limit < 1:
        limit = max_rows
    limit = min(limit, max_rows)
    result = result.head(limit)

    result = result.replace({np.nan: None})

    rows: list[dict[str, Any]] = []
    for _, row in result.iterrows():
        rows.append({str(k): json_safe_scalar(v) for k, v in row.items()})
    return rows
