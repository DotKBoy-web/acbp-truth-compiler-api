from dataclasses import dataclass
from itertools import product
from typing import Iterable, List, Tuple
import pandas as pd

from .engine import Dimension


class MultiACBPRelation:
    """
    Multi-dimensional Al-Anazi Categorical-Boolean Paradigm relation.

    Truth is declared across N categorical dimensions.
    Any undeclared combination is invalid under closed-world masking.
    """

    def __init__(
        self,
        dimensions: List[Dimension],
        valid_tuples: Iterable[Tuple[str, ...]],
        name: str = "Multi-Dimensional ACBP Relation",
    ):
        if len(dimensions) < 2:
            raise ValueError("MultiACBPRelation requires at least two dimensions.")

        self.dimensions = dimensions
        self.valid_tuples = set(tuple(x) for x in valid_tuples)
        self.name = name
        self._validate_tuples()

    def _validate_tuples(self):
        n = len(self.dimensions)

        for t in self.valid_tuples:
            if len(t) != n:
                raise ValueError(f"Tuple {t!r} has length {len(t)}, expected {n}")

            for value, dim in zip(t, self.dimensions):
                if value not in dim.values:
                    raise ValueError(f"{value!r} is not declared in dimension {dim.name!r}")

    def all_tuples(self):
        return list(product(*[dim.values for dim in self.dimensions]))

    def is_valid(self, values: Tuple[str, ...]) -> bool:
        values = tuple(values)
        if len(values) != len(self.dimensions):
            raise ValueError("Input tuple length does not match number of dimensions.")
        return values in self.valid_tuples

    def is_invalid(self, values: Tuple[str, ...]) -> bool:
        return not self.is_valid(values)

    def tuple_vector(self, values: Tuple[str, ...]) -> List[int]:
        vector = []
        for value, dim in zip(values, self.dimensions):
            vector.extend(dim.one_hot(value))
        return vector

    def truth_table(self) -> pd.DataFrame:
        rows = []

        for t in self.all_tuples():
            valid = self.is_valid(t)
            row = {dim.name: value for dim, value in zip(self.dimensions, t)}
            row["truth"] = 1 if valid else 0
            row["state"] = "VALID" if valid else "INVALID"
            row["vector"] = "".join(map(str, self.tuple_vector(t)))
            rows.append(row)

        return pd.DataFrame(rows)

    def valid_table(self) -> pd.DataFrame:
        return self.truth_table().query("truth == 1").reset_index(drop=True)

    def invalid_table(self) -> pd.DataFrame:
        return self.truth_table().query("truth == 0").reset_index(drop=True)

    def dimension_summary(self) -> pd.DataFrame:
        truth = self.truth_table()
        rows = []

        for dim in self.dimensions:
            for value in dim.values:
                subset = truth[truth[dim.name] == value]
                rows.append({
                    "dimension": dim.name,
                    "value": value,
                    "total_combinations": len(subset),
                    "valid_count": int(subset["truth"].sum()),
                    "invalid_count": int((subset["truth"] == 0).sum()),
                    "valid_ratio": round(float(subset["truth"].mean()), 4),
                })

        return pd.DataFrame(rows)

    def export_excel(self, path: str):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.truth_table().to_excel(writer, sheet_name="Truth Table", index=False)
            self.valid_table().to_excel(writer, sheet_name="Valid Tuples", index=False)
            self.invalid_table().to_excel(writer, sheet_name="Invalid Tuples", index=False)
            self.dimension_summary().to_excel(writer, sheet_name="Dimension Summary", index=False)

# ---------------------------------------------------------------------
# Convenience count methods
# ---------------------------------------------------------------------
def _acbp_multi_truth_space_size(self) -> int:
    size = 1
    for dim in self.dimensions:
        size *= len(dim.values)
    return size


def _acbp_multi_declared_valid_count(self) -> int:
    return len(self.valid_tuples)


def _acbp_multi_derived_invalid_count(self) -> int:
    return self.truth_space_size() - self.declared_valid_count()


if not hasattr(MultiACBPRelation, "truth_space_size"):
    MultiACBPRelation.truth_space_size = _acbp_multi_truth_space_size

if not hasattr(MultiACBPRelation, "declared_valid_count"):
    MultiACBPRelation.declared_valid_count = _acbp_multi_declared_valid_count

if not hasattr(MultiACBPRelation, "derived_invalid_count"):
    MultiACBPRelation.derived_invalid_count = _acbp_multi_derived_invalid_count

# ---------------------------------------------------------------------
# Complement invalid tuple API
# ---------------------------------------------------------------------
def _acbp_multi_invalid_tuples(self) -> set[tuple]:
    from itertools import product

    dimension_values = [tuple(dim.values) for dim in self.dimensions]
    all_tuples = set(product(*dimension_values))
    return all_tuples - set(self.valid_tuples)


if not hasattr(MultiACBPRelation, "invalid_tuples"):
    MultiACBPRelation.invalid_tuples = _acbp_multi_invalid_tuples
