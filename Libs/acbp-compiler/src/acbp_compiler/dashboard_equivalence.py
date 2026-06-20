from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


def load_dashboard_result(path: str | Path) -> pd.DataFrame:
    path = Path(path)

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported dashboard result file type: {path.suffix}")


def normalize_dashboard_frame(
    df: pd.DataFrame,
    key_cols: list[str] | None = None,
    ignore_cols: list[str] | None = None,
    round_digits: int = 6,
) -> pd.DataFrame:
    out = df.copy()
    ignore_cols = ignore_cols or []
    key_cols = key_cols or []

    drop_cols = [c for c in ignore_cols if c in out.columns]

    if drop_cols:
        out = out.drop(columns=drop_cols)

    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(round_digits)

    out = out.fillna("")

    ordered_cols = sorted(out.columns)

    if key_cols:
        existing_keys = [c for c in key_cols if c in ordered_cols]
        remaining = [c for c in ordered_cols if c not in existing_keys]
        ordered_cols = existing_keys + remaining

    out = out[ordered_cols]

    if key_cols and all(c in out.columns for c in key_cols):
        out = out.sort_values(key_cols).reset_index(drop=True)
    else:
        out = out.astype(str).sort_values(list(out.columns)).reset_index(drop=True)

    return out


def dashboard_result_hash(
    df: pd.DataFrame,
    key_cols: list[str] | None = None,
    ignore_cols: list[str] | None = None,
    round_digits: int = 6,
) -> str:
    normalized = normalize_dashboard_frame(
        df=df,
        key_cols=key_cols,
        ignore_cols=ignore_cols,
        round_digits=round_digits,
    )

    payload = normalized.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compare_dashboard_results(
    live_df: pd.DataFrame,
    cbp_df: pd.DataFrame,
    key_cols: list[str] | None = None,
    ignore_cols: list[str] | None = None,
    tolerance: float = 0.000001,
    round_digits: int = 6,
) -> dict[str, Any]:
    key_cols = key_cols or []
    ignore_cols = ignore_cols or []

    live_norm = normalize_dashboard_frame(live_df, key_cols, ignore_cols, round_digits)
    cbp_norm = normalize_dashboard_frame(cbp_df, key_cols, ignore_cols, round_digits)

    live_hash = dashboard_result_hash(live_df, key_cols, ignore_cols, round_digits)
    cbp_hash = dashboard_result_hash(cbp_df, key_cols, ignore_cols, round_digits)

    live_cols = list(live_norm.columns)
    cbp_cols = list(cbp_norm.columns)

    common_cols = sorted(set(live_cols).intersection(cbp_cols))
    live_only_cols = sorted(set(live_cols) - set(cbp_cols))
    cbp_only_cols = sorted(set(cbp_cols) - set(live_cols))

    row_count_match = len(live_norm) == len(cbp_norm)
    column_match = live_cols == cbp_cols
    hash_match = live_hash == cbp_hash

    numeric_deltas = []

    if key_cols and all(c in live_norm.columns for c in key_cols) and all(c in cbp_norm.columns for c in key_cols):
        merged = live_norm.merge(
            cbp_norm,
            on=key_cols,
            how="outer",
            suffixes=("_live", "_cbp"),
            indicator=True,
        )

        unmatched_rows = int((merged["_merge"] != "both").sum())

        for col in common_cols:
            if col in key_cols:
                continue

            live_col = f"{col}_live"
            cbp_col = f"{col}_cbp"

            if live_col not in merged.columns or cbp_col not in merged.columns:
                continue

            live_num = pd.to_numeric(merged[live_col], errors="coerce")
            cbp_num = pd.to_numeric(merged[cbp_col], errors="coerce")

            if live_num.notna().any() or cbp_num.notna().any():
                delta = (live_num - cbp_num).abs()
                max_delta = float(delta.max(skipna=True)) if delta.notna().any() else 0.0

                numeric_deltas.append({
                    "metric": col,
                    "max_abs_delta": max_delta,
                    "within_tolerance": bool(max_delta <= tolerance),
                })

    else:
        unmatched_rows = None

        if live_norm.shape == cbp_norm.shape and live_cols == cbp_cols:
            for col in common_cols:
                live_num = pd.to_numeric(live_norm[col], errors="coerce")
                cbp_num = pd.to_numeric(cbp_norm[col], errors="coerce")

                if live_num.notna().any() or cbp_num.notna().any():
                    delta = (live_num - cbp_num).abs()
                    max_delta = float(delta.max(skipna=True)) if delta.notna().any() else 0.0

                    numeric_deltas.append({
                        "metric": col,
                        "max_abs_delta": max_delta,
                        "within_tolerance": bool(max_delta <= tolerance),
                    })

    numeric_match = all(item["within_tolerance"] for item in numeric_deltas)

    return {
        "semantic_equivalence": bool(hash_match or (row_count_match and column_match and numeric_match)),
        "hash_match": bool(hash_match),
        "row_count_match": bool(row_count_match),
        "column_match": bool(column_match),
        "numeric_match": bool(numeric_match),
        "live_hash": live_hash,
        "cbp_hash": cbp_hash,
        "live_rows": int(len(live_norm)),
        "cbp_rows": int(len(cbp_norm)),
        "live_columns": live_cols,
        "cbp_columns": cbp_cols,
        "live_only_columns": live_only_cols,
        "cbp_only_columns": cbp_only_cols,
        "unmatched_rows": unmatched_rows,
        "numeric_deltas": numeric_deltas,
        "guardrail": (
            "Hash equality means deterministic equivalence after normalization. "
            "If hashes differ, numeric tolerance and row/column checks explain whether the paths are still semantically equivalent."
        ),
    }


def latency_comparison(
    live_ms: float,
    cbp_ms: float,
) -> dict[str, Any]:
    live_ms = float(live_ms)
    cbp_ms = float(cbp_ms)

    if cbp_ms <= 0:
        speedup = None
    else:
        speedup = live_ms / cbp_ms

    return {
        "live_ms": live_ms,
        "cbp_ms": cbp_ms,
        "speedup_factor": speedup,
        "faster_path": "cbp" if cbp_ms < live_ms else "live_sql",
    }


def compare_dashboard_result_files(
    live_path: str | Path,
    cbp_path: str | Path,
    key_cols: list[str] | None = None,
    ignore_cols: list[str] | None = None,
    tolerance: float = 0.000001,
) -> dict[str, Any]:
    live_df = load_dashboard_result(live_path)
    cbp_df = load_dashboard_result(cbp_path)

    return compare_dashboard_results(
        live_df=live_df,
        cbp_df=cbp_df,
        key_cols=key_cols,
        ignore_cols=ignore_cols,
        tolerance=tolerance,
    )
