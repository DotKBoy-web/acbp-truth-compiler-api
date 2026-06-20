from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ACBPBinner:
    n_bins: int = 3
    max_categories: int = 30
    low_cardinality_numeric_as_category: int = 10
    transformers_: dict = field(default_factory=dict)

    def fit(self, X: pd.DataFrame) -> "ACBPBinner":
        self.transformers_ = {}

        labels = [f"B{i + 1}" for i in range(self.n_bins)]

        for col in X.columns:
            s = X[col]
            unique_count = int(s.nunique(dropna=True))

            numeric_should_be_binned = (
                pd.api.types.is_numeric_dtype(s)
                and unique_count > self.low_cardinality_numeric_as_category
            )

            if numeric_should_be_binned:
                thresholds = [
                    float(s.quantile(i / self.n_bins))
                    for i in range(1, self.n_bins)
                ]

                self.transformers_[col] = {
                    "type": "numeric",
                    "labels": labels,
                    "thresholds": thresholds,
                    "values": labels,
                }

            else:
                values = (
                    s.astype(str)
                    .fillna("Missing")
                    .replace({"nan": "Missing", "None": "Missing", "": "Missing"})
                )

                cats = list(values.value_counts().head(self.max_categories).index)

                if "Other" not in cats:
                    cats.append("Other")

                self.transformers_[col] = {
                    "type": "categorical",
                    "categories": cats,
                    "values": cats,
                }

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.transformers_:
            raise RuntimeError("ACBPBinner is not fitted.")

        out = pd.DataFrame(index=X.index)

        for col, t in self.transformers_.items():
            if col not in X.columns:
                raise KeyError(f"Missing column: {col}")

            if t["type"] == "numeric":
                labels = t["labels"]
                thresholds = t["thresholds"]

                def bin_value(x):
                    if pd.isna(x):
                        return "Missing"
                    for i, threshold in enumerate(thresholds):
                        if float(x) <= threshold:
                            return labels[i]
                    return labels[-1]

                out[col] = X[col].apply(bin_value).astype(str)

            else:
                categories = set(t["categories"])

                def cat_value(x):
                    value = str(x)
                    if value in ["nan", "None", ""]:
                        value = "Missing"
                    return value if value in categories else "Other"

                out[col] = X[col].apply(cat_value).astype(str)

        return out

    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return self.fit(X).transform(X)

    def dimension_values(self, column: str) -> list[str]:
        return list(self.transformers_[column]["values"])
