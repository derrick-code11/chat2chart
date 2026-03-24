from __future__ import annotations

from typing import Any

from app.core.errors import CHART_GENERATION_FAILED, VALIDATION_ERROR, AppError

_ALLOWED_TYPES = frozenset({"bar", "line", "pie", "stacked_bar"})


def _encoding_field(enc: dict[str, Any], key: str) -> str:
    block = enc.get(key)
    if not isinstance(block, dict):
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"encoding.{key} must be an object with a field.",
        )
    fn = block.get("field")
    if fn is None or not str(fn).strip():
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"encoding.{key}.field is required.",
        )
    return str(fn)


def validate_chart_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise AppError(422, VALIDATION_ERROR, "chart_spec must be an object.")

    ver = spec.get("version")
    if ver is not None and ver != 1:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            "chart_spec.version must be 1.",
        )

    chart_type = spec.get("type")
    if chart_type not in _ALLOWED_TYPES:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"chart_spec.type must be one of: {sorted(_ALLOWED_TYPES)}.",
        )

    data = spec.get("data")
    if not isinstance(data, dict):
        raise AppError(422, CHART_GENERATION_FAILED, "chart_spec.data must be an object.")
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) == 0:
        raise AppError(422, CHART_GENERATION_FAILED, "chart_spec.data.rows must be a non-empty array.")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AppError(
                422,
                CHART_GENERATION_FAILED,
                f"chart_spec.data.rows[{i}] must be an object.",
            )

    enc = spec.get("encoding")
    if not isinstance(enc, dict):
        raise AppError(422, CHART_GENERATION_FAILED, "chart_spec.encoding must be an object.")

    if chart_type in ("bar", "line"):
        xf = _encoding_field(enc, "x")
        yf = _encoding_field(enc, "y")
        for i, row in enumerate(rows):
            for f in (xf, yf):
                if f not in row:
                    raise AppError(
                        422,
                        CHART_GENERATION_FAILED,
                        f"Row {i} missing field {f!r} for {chart_type} chart.",
                    )
    elif chart_type == "pie":
        lf = None
        vf = None
        if "label" in enc and "value" in enc:
            lf = _encoding_field(enc, "label")
            vf = _encoding_field(enc, "value")
        elif "x" in enc and "y" in enc:
            lf = _encoding_field(enc, "x")
            vf = _encoding_field(enc, "y")
        else:
            raise AppError(
                422,
                CHART_GENERATION_FAILED,
                "pie charts need encoding.label+value or encoding.x+y.",
            )
        for i, row in enumerate(rows):
            for f in (lf, vf):
                if f not in row:
                    raise AppError(
                        422,
                        CHART_GENERATION_FAILED,
                        f"Row {i} missing field {f!r} for pie chart.",
                    )
    else:  # stacked_bar
        xf = _encoding_field(enc, "x")
        sf = _encoding_field(enc, "series")
        yf = _encoding_field(enc, "y")
        for i, row in enumerate(rows):
            for f in (xf, sf, yf):
                if f not in row:
                    raise AppError(
                        422,
                        CHART_GENERATION_FAILED,
                        f"Row {i} missing field {f!r} for stacked_bar chart.",
                    )

    return spec
