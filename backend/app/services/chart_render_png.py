from __future__ import annotations

import asyncio
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

from app.core.errors import CHART_GENERATION_FAILED, VALIDATION_ERROR, AppError


def _field_name(enc: dict[str, Any], key: str) -> str | None:
    block = enc.get(key)
    if isinstance(block, dict):
        fn = block.get("field")
        if fn is not None:
            return str(fn)
    return None


def _row_value(row: dict[str, Any], field: str) -> Any:
    if field not in row:
        raise AppError(422, VALIDATION_ERROR, f"Row missing field {field!r}.")
    return row[field]


def _coerce_float(v: Any) -> float:
    if v is None:
        raise ValueError("null")
    return float(v)


def _palette_colors(palette: list[str] | None, n: int) -> list:
    if palette and len(palette) >= n:
        return [palette[i % len(palette)] for i in range(n)]
    base = list(plt.cm.tab20.colors)
    return [base[i % len(base)] for i in range(n)]


def chart_spec_to_png_bytes(spec: dict[str, Any]) -> bytes:
    if not isinstance(spec, dict):
        raise AppError(422, VALIDATION_ERROR, "Invalid chart_spec.")

    data = spec.get("data")
    rows = data.get("rows") if isinstance(data, dict) else None
    if not rows or not isinstance(rows, list):
        raise AppError(422, VALIDATION_ERROR, "chart_spec has no data.rows.")
    for r in rows:
        if not isinstance(r, dict):
            raise AppError(422, VALIDATION_ERROR, "data.rows must be objects.")

    enc = spec.get("encoding") if isinstance(spec.get("encoding"), dict) else {}
    chart_type = str(spec.get("type") or "bar")
    title = (spec.get("title") or "Chart")[:200]
    style = spec.get("style") if isinstance(spec.get("style"), dict) else {}
    palette = style.get("palette") if isinstance(style.get("palette"), list) else None

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=120)
    try:
        if chart_type in ("bar", "line"):
            xf = _field_name(enc, "x")
            yf = _field_name(enc, "y")
            if not xf or not yf:
                raise AppError(
                    422,
                    VALIDATION_ERROR,
                    "bar/line charts require encoding.x.field and encoding.y.field.",
                )
            xs = [_row_value(r, xf) for r in rows]
            ys = [_coerce_float(_row_value(r, yf)) for r in rows]
            x_label = enc.get("x", {}).get("label") if isinstance(enc.get("x"), dict) else xf
            y_label = enc.get("y", {}).get("label") if isinstance(enc.get("y"), dict) else yf
            colors = _palette_colors(
                [str(c) for c in palette] if palette else None, len(xs)
            )
            if chart_type == "bar":
                ax.bar(range(len(xs)), ys, color=colors[: len(ys)])
                ax.set_xticks(range(len(xs)))
                ax.set_xticklabels([str(x) for x in xs], rotation=35, ha="right")
            else:
                ax.plot(range(len(xs)), ys, marker="o", color=colors[0] if colors else None)
                ax.set_xticks(range(len(xs)))
                ax.set_xticklabels([str(x) for x in xs], rotation=35, ha="right")
            ax.set_xlabel(str(x_label or xf))
            ax.set_ylabel(str(y_label or yf))
            ax.set_title(title)
            ax.grid(True, alpha=0.25)

        elif chart_type == "pie":
            lf = _field_name(enc, "label") or _field_name(enc, "x")
            vf = _field_name(enc, "value") or _field_name(enc, "y")
            if not lf or not vf:
                raise AppError(
                    422,
                    VALIDATION_ERROR,
                    "pie charts require encoding.label/value (or x/y) fields.",
                )
            labels = [str(_row_value(r, lf)) for r in rows]
            sizes = [_coerce_float(_row_value(r, vf)) for r in rows]
            cols = _palette_colors(
                [str(c) for c in palette] if palette else None, len(labels)
            )
            ax.pie(sizes, labels=labels, autopct="%1.0f%%", colors=cols)
            ax.set_title(title)

        elif chart_type == "stacked_bar":
            xf = _field_name(enc, "x")
            sf = _field_name(enc, "series")
            yf = _field_name(enc, "y")
            if not xf or not sf or not yf:
                raise AppError(
                    422,
                    VALIDATION_ERROR,
                    "stacked_bar requires encoding.x, encoding.series, and encoding.y.",
                )
            df = pd.DataFrame(rows)
            for col in (xf, sf, yf):
                if col not in df.columns:
                    raise AppError(
                        422,
                        VALIDATION_ERROR,
                        f"stacked_bar rows must include field {col!r}.",
                    )
            pivot = df.pivot_table(
                index=xf,
                columns=sf,
                values=yf,
                aggfunc="sum",
                fill_value=0,
            )
            colors = _palette_colors(
                [str(c) for c in palette] if palette else None, pivot.shape[1]
            )
            pivot.plot(kind="bar", stacked=True, ax=ax, color=colors)
            ax.set_title(title)
            ax.legend(title=str(enc.get("series", {}).get("label", sf)), bbox_to_anchor=(1.02, 1))
            ax.set_xlabel(str(enc.get("x", {}).get("label", xf)))
            ax.set_ylabel(str(enc.get("y", {}).get("label", yf)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right")

        else:
            raise AppError(
                422,
                VALIDATION_ERROR,
                f"Unsupported chart type for PNG export: {chart_type!r}.",
            )

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        return buf.getvalue()
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            422,
            CHART_GENERATION_FAILED,
            f"Could not render chart to PNG: {e}",
        ) from e
    finally:
        plt.close(fig)


async def chart_spec_to_png_bytes_async(spec: dict[str, Any]) -> bytes:
    return await asyncio.to_thread(chart_spec_to_png_bytes, spec)
