from __future__ import annotations

from dataclasses import dataclass
import json
import pandas as pd


@dataclass
class ACBPColumnProfile:
    name: str
    dtype: str
    role_guess: str
    n_rows: int
    n_missing: int
    missing_rate: float
    n_unique: int
    unique_rate: float
    is_numeric: bool
    is_candidate_target: bool
    recommended_bins: int
    sample_values: str


class ACBPDatasetProfiler:
    @staticmethod
    def profile(df: pd.DataFrame, target_col: str | None = None) -> dict:
        if df is None or len(df.columns) == 0:
            raise ValueError("Dataset is empty or has no columns.")

        n_rows = int(len(df))
        rows = []
        candidate_targets = []

        for col in df.columns:
            s = df[col]
            n_missing = int(s.isna().sum())
            missing_rate = float(n_missing / n_rows) if n_rows else 0.0
            n_unique = int(s.nunique(dropna=True))
            unique_rate = float(n_unique / n_rows) if n_rows else 0.0
            is_numeric = bool(pd.api.types.is_numeric_dtype(s))

            is_candidate_target = (
                n_rows > 0
                and 2 <= n_unique <= min(50, max(2, int(n_rows * 0.30)))
                and missing_rate < 0.20
            )

            if col == target_col:
                role_guess = "selected_target"
            elif is_candidate_target:
                role_guess = "candidate_target_or_categorical_dimension"
                candidate_targets.append(col)
            elif is_numeric:
                role_guess = "numeric_dimension_candidate"
            else:
                role_guess = "categorical_dimension_candidate"

            recommended_bins = 3
            if is_numeric and n_unique > 50:
                recommended_bins = 4
            if is_numeric and n_unique > 200:
                recommended_bins = 5

            sample = (
                s.dropna()
                .astype(str)
                .drop_duplicates()
                .head(8)
                .tolist()
            )

            rows.append({
                "column": col,
                "dtype": str(s.dtype),
                "role_guess": role_guess,
                "n_rows": n_rows,
                "n_missing": n_missing,
                "missing_rate": round(missing_rate, 4),
                "n_unique": n_unique,
                "unique_rate": round(unique_rate, 4),
                "is_numeric": is_numeric,
                "is_candidate_target": is_candidate_target,
                "recommended_bins": recommended_bins,
                "sample_values": json.dumps(sample, ensure_ascii=False),
            })

        columns_df = pd.DataFrame(rows)

        return {
            "n_rows": n_rows,
            "n_columns": int(len(df.columns)),
            "columns": columns_df,
            "candidate_targets": candidate_targets,
            "selected_target": target_col,
        }

    @staticmethod
    def recommend_features(df: pd.DataFrame, target_col: str, max_features: int = 8) -> list[str]:
        candidates = []

        for col in df.columns:
            if col == target_col:
                continue

            s = df[col]
            n_rows = max(len(s), 1)
            missing_rate = float(s.isna().sum() / n_rows)
            n_unique = int(s.nunique(dropna=True))
            unique_rate = float(n_unique / n_rows)
            is_numeric = bool(pd.api.types.is_numeric_dtype(s))

            score = 0.0

            if missing_rate < 0.10:
                score += 2.0
            elif missing_rate < 0.30:
                score += 1.0
            else:
                score -= 2.0

            if is_numeric:
                score += 2.0
                if n_unique >= 10:
                    score += 1.0
            else:
                if 2 <= n_unique <= 30:
                    score += 2.0
                elif n_unique > 30:
                    score -= 1.0

            if unique_rate > 0.95:
                score -= 3.0

            candidates.append((score, col))

        candidates.sort(reverse=True)
        return [col for _, col in candidates[:max_features]]
