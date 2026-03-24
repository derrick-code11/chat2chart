from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.errors import VALIDATION_ERROR, AppError

_ALLOWED_EXT = {".csv", ".xlsx", ".xls"}


def extension_from_filename(filename: str) -> str:
    lower = filename.lower().strip()
    for ext in _ALLOWED_EXT:
        if lower.endswith(ext):
            return ext
    return ""


def _sanitize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    names: list[str] = []
    used: dict[str, bool] = {}
    for i, col in enumerate(df.columns):
        base = str(col).strip() if col is not None else ""
        if not base:
            base = f"column_{i}"
        candidate = base
        n = 1
        while candidate in used:
            candidate = f"{base}_{n}"
            n += 1
        used[candidate] = True
        names.append(candidate)
    df.columns = names
    return df


def json_safe_scalar(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, np.generic):
        return value.item() if hasattr(value, "item") else str(value)
    return str(value)


def _infer_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        sample = series.dropna().head(80)
        if sample.empty:
            return "text"
        parsed = pd.to_datetime(sample, errors="coerce", utc=False)
        if parsed.notna().mean() >= 0.75:
            return "date"
        return "text"
    return "unknown"


def _sample_values(series: pd.Series, limit: int = 5) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for val in series.dropna().head(200):
        safe = json_safe_scalar(val)
        key = repr(safe)
        if key in seen:
            continue
        seen.add(key)
        out.append(safe)
        if len(out) >= limit:
            break
    return out


def read_tabular_head(content: bytes, original_filename: str, nrows: int) -> pd.DataFrame:
    """Read only the first `nrows` rows for preview (faster on large files)."""
    ext = extension_from_filename(original_filename)
    if ext not in _ALLOWED_EXT:
        raise AppError(
            400,
            VALIDATION_ERROR,
            "Unsupported file type.",
            details={"filename": original_filename},
        )
    buf = io.BytesIO(content)
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(buf, encoding="utf-8", nrows=nrows)
            except UnicodeDecodeError:
                buf.seek(0)
                df = pd.read_csv(buf, encoding="latin-1", nrows=nrows)
        elif ext == ".xlsx":
            df = pd.read_excel(buf, sheet_name=0, engine="openpyxl", nrows=nrows)
        else:
            df = pd.read_excel(buf, sheet_name=0, engine="xlrd", nrows=nrows)
    except Exception as e:
        raise AppError(
            400,
            VALIDATION_ERROR,
            f"Could not read spreadsheet preview: {e}",
        ) from e
    if df.empty or len(df.columns) == 0:
        raise AppError(400, VALIDATION_ERROR, "The file has no rows or columns.")
    return _sanitize_column_names(df)


def read_tabular(content: bytes, original_filename: str) -> pd.DataFrame:
    ext = extension_from_filename(original_filename)
    if ext not in _ALLOWED_EXT:
        raise AppError(
            400,
            VALIDATION_ERROR,
            "Unsupported file type. Upload a .csv, .xlsx, or .xls file.",
            details={"filename": original_filename},
        )
    buf = io.BytesIO(content)
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(buf, encoding="utf-8")
            except UnicodeDecodeError:
                buf.seek(0)
                df = pd.read_csv(buf, encoding="latin-1")
        elif ext == ".xlsx":
            df = pd.read_excel(buf, sheet_name=0, engine="openpyxl")
        else:
            df = pd.read_excel(buf, sheet_name=0, engine="xlrd")
    except Exception as e:
        raise AppError(
            400,
            VALIDATION_ERROR,
            f"Could not read spreadsheet: {e}",
        ) from e

    if df.empty or len(df.columns) == 0:
        raise AppError(400, VALIDATION_ERROR, "The file has no rows or columns.")

    df = _sanitize_column_names(df)
    return df


def build_column_metadata(df: pd.DataFrame) -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    for ordinal, col in enumerate(df.columns):
        series = df[col]
        inferred = _infer_type(series)
        meta.append(
            {
                "ordinal": ordinal,
                "name": str(col),
                "inferred_type": inferred,
                "sample_values": _sample_values(series),
            }
        )
    return meta


def preview_records(df: pd.DataFrame, max_rows: int) -> tuple[list[dict[str, Any]], bool]:
    """Return JSON-serializable row dicts and whether the preview is truncated."""
    head = df.head(max_rows)
    truncated = len(df) > len(head)
    rows: list[dict[str, Any]] = []
    for _, row in head.iterrows():
        record: dict[str, Any] = {}
        for k, v in row.items():
            record[str(k)] = json_safe_scalar(v)
        rows.append(record)
    return rows, truncated


def normalize_filename(name: str | None) -> str:
    if not name or not str(name).strip():
        return "upload"
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(str(name)).name).strip("._")
    return base or "upload"
