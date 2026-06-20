from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ACBPCompactFeatureSelector:
    n_bins: int = 3
    max_features: int = 6
    max_truth_space: int = 20_000
    min_density: float = 0.02
    max_categories: int = 30
    low_cardinality_numeric_as_category: int = 10

    def feature_cardinality(self, s: pd.Series) -> int:
        unique = int(s.nunique(dropna=True))

        if unique <= 0:
            return 1

        if pd.api.types.is_numeric_dtype(s) and unique > self.low_cardinality_numeric_as_category:
            return int(self.n_bins)

        if unique > self.max_categories:
            return int(self.max_categories + 1)

        return int(unique + 1)

    def reject_reason(self, df: pd.DataFrame, feature: str) -> str | None:
        name = feature.lower().strip()
        n = max(int(len(df)), 1)
        unique = int(df[feature].nunique(dropna=True))
        unique_ratio = unique / n

        hard_patterns = [
            "id", "case_id", "mrn", "person", "patient_name", "name",
            "date", "time", "timestamp", "scheduled_start", "actual_start",
            "start_time", "end_time", "created", "updated",
        ]

        if name in {"case_id", "patient_id", "encounter_id"}:
            return "Identifier column; creates memorization rather than reusable truth."

        if name.endswith("_id") or name == "id":
            return "Identifier column; creates memorization rather than reusable truth."

        if any(pattern in name for pattern in hard_patterns):
            return "Date/time/identifier-like column; not suitable for compact declared-truth modeling."

        raw_measure_patterns = [
            "start_delay_min",
            "surgery_duration_min",
            "turnover_min",
            "_min",
            "minutes",
            "duration_min",
            "delay_min",
        ]

        if any(pattern in name for pattern in raw_measure_patterns):
            return "Raw continuous measurement; prefer its bucketed categorical version."

        if unique_ratio >= 0.35 and unique >= 30:
            return f"Too many distinct values ({unique}); would make truth space sparse."

        return None

    def name_bonus(self, feature: str) -> float:
        name = feature.lower()
        bonus = 0.0

        if "bucket" in name:
            bonus += 1.10
        if "flag" in name:
            bonus += 0.60
        if "priority" in name:
            bonus += 0.55
        if "asa" in name:
            bonus += 0.50
        if "class" in name:
            bonus += 0.35
        if "type" in name:
            bonus += 0.25
        if "group" in name:
            bonus += 0.20
        if "service" in name:
            bonus += 0.15

        return bonus

    def score_feature(self, df: pd.DataFrame, target_col: str, feature: str) -> dict[str, Any]:
        reject_reason = self.reject_reason(df, feature)
        cardinality = self.feature_cardinality(df[feature])

        if reject_reason:
            return {
                "feature": feature,
                "score": -999.0,
                "cardinality": int(cardinality),
                "purity": 0.0,
                "baseline": 0.0,
                "lift": 0.0,
                "excluded": True,
                "reason": reject_reason,
            }

        y = df[target_col].astype(str)
        x = df[feature]

        if pd.api.types.is_numeric_dtype(x) and x.nunique(dropna=True) > self.low_cardinality_numeric_as_category:
            try:
                labels = [f"B{i + 1}" for i in range(self.n_bins)]
                xb = pd.qcut(
                    x.rank(method="first"),
                    q=self.n_bins,
                    labels=labels,
                    duplicates="drop",
                ).astype(str)
            except Exception:
                xb = x.astype(str)
        else:
            xb = (
                x.astype(str)
                .fillna("Missing")
                .replace({"nan": "Missing", "None": "Missing", "": "Missing"})
            )

        tmp = pd.DataFrame({"x": xb, "y": y}).dropna()

        if tmp.empty:
            return {
                "feature": feature,
                "score": -999.0,
                "cardinality": 1,
                "purity": 0.0,
                "baseline": 0.0,
                "lift": 0.0,
                "excluded": True,
                "reason": "No usable values.",
            }

        baseline = float(tmp["y"].value_counts(normalize=True).max())

        grouped = tmp.groupby("x")["y"].value_counts(normalize=True).rename("p").reset_index()
        purity_by_group = grouped.groupby("x")["p"].max()
        group_weights = tmp["x"].value_counts(normalize=True)

        weighted_purity = float(
            sum(purity_by_group[group] * group_weights[group] for group in purity_by_group.index)
        )

        lift = weighted_purity - baseline
        name_bonus = self.name_bonus(feature)

        score = float(
            (lift * 10.0)
            + weighted_purity
            + name_bonus
            - (0.12 * max(cardinality - 2, 0))
        )

        return {
            "feature": feature,
            "score": round(score, 6),
            "cardinality": int(cardinality),
            "purity": round(weighted_purity, 6),
            "baseline": round(baseline, 6),
            "lift": round(lift, 6),
            "name_bonus": round(name_bonus, 6),
            "excluded": False,
            "reason": (
                f"purity={weighted_purity:.3f}, "
                f"lift={lift:.3f}, "
                f"cardinality={cardinality}, "
                f"name_bonus={name_bonus:.2f}"
            ),
        }

    def select(
        self,
        df: pd.DataFrame,
        target_col: str,
        candidate_features: list[str] | None = None,
    ) -> dict[str, Any]:
        clean = df.dropna(subset=[target_col]).copy()
        clean[target_col] = clean[target_col].astype(str)

        if candidate_features is None or not candidate_features:
            candidate_features = [column for column in clean.columns if column != target_col]

        candidate_features = [
            column for column in candidate_features
            if column in clean.columns and column != target_col
        ]

        target_cardinality = max(int(clean[target_col].nunique(dropna=True)), 1)
        n_rows = max(int(len(clean)), 1)

        all_scored = [
            self.score_feature(clean, target_col, feature)
            for feature in candidate_features
        ]

        excluded = [item for item in all_scored if item.get("excluded")]
        scored = [item for item in all_scored if not item.get("excluded")]

        scored = sorted(
            scored,
            key=lambda row: (row["score"], -row["cardinality"]),
            reverse=True,
        )

        selected = []
        rejected = []
        current_space = target_cardinality

        for item in scored:
            proposed_space = current_space * max(int(item["cardinality"]), 1)
            proposed_declared_upper = min(n_rows, proposed_space)
            proposed_density = proposed_declared_upper / proposed_space if proposed_space else 0

            can_add = (
                len(selected) < self.max_features
                and proposed_space <= self.max_truth_space
                and proposed_density >= self.min_density
            )

            if len(selected) < 2 and proposed_space <= self.max_truth_space:
                can_add = True

            if can_add:
                selected.append(item)
                current_space = proposed_space
            else:
                rejected_item = dict(item)
                rejected_item["rejected_reason"] = (
                    f"Would make truth_space={proposed_space:,}, "
                    f"density_upper={proposed_density:.6f}"
                )
                rejected.append(rejected_item)

        selected_features = [item["feature"] for item in selected]
        declared_upper = min(n_rows, current_space)
        density_upper = declared_upper / current_space if current_space else 0

        return {
            "selected_features": selected_features,
            "selected_details": selected,
            "rejected_details": rejected,
            "excluded_details": excluded,
            "estimate": {
                "target_cardinality": target_cardinality,
                "n_rows": n_rows,
                "truth_space_size": int(current_space),
                "declared_upper_bound": int(declared_upper),
                "density_upper_bound": float(density_upper),
                "max_truth_space": int(self.max_truth_space),
                "min_density": float(self.min_density),
            },
            "advice": (
                "Selected compact, reusable dimensions and excluded identifiers, dates, times, "
                "and raw continuous measurements that would create fake truth-space sparsity."
            ),
        }


def auto_compact_features(
    df: pd.DataFrame,
    target_col: str,
    candidate_features: list[str] | None = None,
    n_bins: int = 3,
    max_features: int = 6,
    max_truth_space: int = 20_000,
    min_density: float = 0.02,
) -> dict[str, Any]:
    selector = ACBPCompactFeatureSelector(
        n_bins=n_bins,
        max_features=max_features,
        max_truth_space=max_truth_space,
        min_density=min_density,
    )

    return selector.select(
        df=df,
        target_col=target_col,
        candidate_features=candidate_features,
    )
