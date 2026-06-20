from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from acbp import Dimension, MultiACBPRelation
from acbp_ml.binning import ACBPBinner


@dataclass
class ACBPSmoothRiskPolicy:
    risk_class: str | None = None
    risk_bias: float = 0.0
    support_bonus: float = 0.0
    exact_bonus: float = 0.0


@dataclass
class ACBPClassifier:
    n_bins: int = 3
    max_categories: int = 30
    policy: ACBPSmoothRiskPolicy = field(default_factory=ACBPSmoothRiskPolicy)

    binner_: ACBPBinner | None = None
    relation_: MultiACBPRelation | None = None
    class_names_: list[str] = field(default_factory=list)
    feature_names_: list[str] = field(default_factory=list)
    valid_tuples_counter_: Counter = field(default_factory=Counter)
    class_feature_tuples_: dict = field(default_factory=lambda: defaultdict(Counter))
    class_prior_: Counter = field(default_factory=Counter)

    def fit(self, X: pd.DataFrame, y: pd.Series | list[Any]) -> "ACBPClassifier":
        X = pd.DataFrame(X).copy()
        y = pd.Series(y, index=X.index).astype(str)

        self.feature_names_ = list(X.columns)
        self.class_names_ = sorted(y.dropna().astype(str).unique().tolist())

        self.binner_ = ACBPBinner(
            n_bins=self.n_bins,
            max_categories=self.max_categories,
        )

        Xb = self.binner_.fit_transform(X)

        self.valid_tuples_counter_ = Counter()
        self.class_feature_tuples_ = defaultdict(Counter)
        self.class_prior_ = Counter(y.astype(str).tolist())

        for idx in Xb.index:
            cls = str(y.loc[idx])
            bins = tuple(str(Xb.loc[idx, c]) for c in self.feature_names_)
            full = tuple([cls, *bins])

            self.valid_tuples_counter_[full] += 1
            self.class_feature_tuples_[cls][bins] += 1

        dimensions = [Dimension("TargetClass", self.class_names_)]

        for feature in self.feature_names_:
            dimensions.append(
                Dimension(
                    feature.replace(" ", "_"),
                    self.binner_.dimension_values(feature),
                )
            )

        self.relation_ = MultiACBPRelation(
            dimensions=dimensions,
            valid_tuples=set(self.valid_tuples_counter_.keys()),
            name="ACBPClassifier Truth Space",
        )

        return self

    def _check_fitted(self) -> None:
        if self.binner_ is None or self.relation_ is None:
            raise RuntimeError("ACBPClassifier is not fitted.")

    @staticmethod
    def _hamming(a: tuple, b: tuple) -> int:
        return sum(x != y for x, y in zip(a, b))

    def _nearest_for_class(self, cls: str, bins: tuple) -> tuple[int, tuple | None, int]:
        candidates = self.class_feature_tuples_[cls]

        best_distance = None
        best_bins = None
        best_support = 0

        for candidate_bins, support in candidates.items():
            dist = self._hamming(bins, candidate_bins)

            if (
                best_distance is None
                or dist < best_distance
                or (dist == best_distance and support > best_support)
            ):
                best_distance = dist
                best_bins = candidate_bins
                best_support = int(support)

        if best_distance is None:
            return 999, None, 0

        return int(best_distance), best_bins, int(best_support)

    def score_one(self, bins: tuple) -> list[dict]:
        self._check_fitted()

        rows = []

        for cls in self.class_names_:
            full = tuple([cls, *bins])
            exact_support = int(self.valid_tuples_counter_.get(full, 0))
            nearest_distance, nearest_bins, nearest_support = self._nearest_for_class(cls, bins)

            score = float(nearest_distance)
            score -= float(self.policy.support_bonus) * np.log1p(nearest_support)
            score -= float(self.policy.exact_bonus) * np.log1p(exact_support)

            if self.policy.risk_class is not None and cls == str(self.policy.risk_class):
                score -= float(self.policy.risk_bias)

            rows.append({
                "class": cls,
                "policy_score": score,
                "exact_support": exact_support,
                "nearest_distance": nearest_distance,
                "nearest_support": nearest_support,
                "nearest_bins": nearest_bins,
                "class_prior": int(self.class_prior_[cls]),
            })

        return sorted(
            rows,
            key=lambda r: (
                r["policy_score"],
                r["nearest_distance"],
                -r["exact_support"],
                -r["nearest_support"],
                r["class"],
            ),
        )

    def predict(self, X: pd.DataFrame) -> list[str]:
        self._check_fitted()

        X = pd.DataFrame(X).copy()
        Xb = self.binner_.transform(X)

        preds = []

        for idx in Xb.index:
            bins = tuple(str(Xb.loc[idx, c]) for c in self.feature_names_)
            ranked = self.score_one(bins)
            preds.append(ranked[0]["class"])

        return preds

    def predict_frame(self, X: pd.DataFrame, y: pd.Series | list[Any] | None = None) -> pd.DataFrame:
        self._check_fitted()

        X = pd.DataFrame(X).copy()
        Xb = self.binner_.transform(X)

        y_series = None
        if y is not None:
            y_series = pd.Series(y, index=X.index).astype(str)

        rows = []

        for idx in Xb.index:
            bins = tuple(str(Xb.loc[idx, c]) for c in self.feature_names_)
            ranked = self.score_one(bins)
            winner = ranked[0]

            row = {
                "row_id": idx,
                "predicted": winner["class"],
                "bins": " | ".join(bins),
                "winner_policy_score": winner["policy_score"],
                "winner_exact_support": winner["exact_support"],
                "winner_nearest_distance": winner["nearest_distance"],
                "winner_nearest_support": winner["nearest_support"],
                "candidate_scores": ranked,
            }

            if y_series is not None:
                actual = str(y_series.loc[idx])
                row["actual"] = actual
                row["correct"] = actual == winner["class"]

            for r in ranked:
                cls = r["class"]
                row[f"{cls}_score"] = r["policy_score"]
                row[f"{cls}_distance"] = r["nearest_distance"]
                row[f"{cls}_exact_support"] = r["exact_support"]
                row[f"{cls}_nearest_support"] = r["nearest_support"]

            rows.append(row)

        return pd.DataFrame(rows)

    def explain(self, X: pd.DataFrame, row_index: int | None = None) -> dict:
        self._check_fitted()

        X = pd.DataFrame(X).copy()

        if row_index is None:
            row_index = X.index[0]

        Xb = self.binner_.transform(X.loc[[row_index]])
        bins = tuple(str(Xb.loc[row_index, c]) for c in self.feature_names_)
        ranked = self.score_one(bins)

        return {
            "row_id": row_index,
            "bins": bins,
            "prediction": ranked[0]["class"],
            "ranked_candidates": ranked,
            "truth_space_size": self.relation_.truth_space_size(),
            "declared_valid_count": self.relation_.declared_valid_count(),
            "derived_invalid_count": self.relation_.derived_invalid_count(),
        }

    def evaluate(self, X: pd.DataFrame, y: pd.Series | list[Any]) -> dict:
        pred = self.predict(X)
        y_true = pd.Series(y).astype(str).tolist()

        cm = confusion_matrix(y_true, pred, labels=self.class_names_)

        return {
            "accuracy": float(accuracy_score(y_true, pred)),
            "confusion_matrix": pd.DataFrame(
                cm,
                index=[f"actual_{c}" for c in self.class_names_],
                columns=[f"pred_{c}" for c in self.class_names_],
            ),
            "classification_report": pd.DataFrame(
                classification_report(
                    y_true,
                    pred,
                    labels=self.class_names_,
                    output_dict=True,
                    zero_division=0,
                )
            ).T,
        }
