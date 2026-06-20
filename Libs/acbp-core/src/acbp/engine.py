from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable
import pandas as pd


@dataclass
class Dimension:
    name: str
    values: List[str]

    def one_hot(self, value: str) -> List[int]:
        if value not in self.values:
            raise ValueError(f"{value!r} is not declared in dimension {self.name!r}")
        return [1 if v == value else 0 for v in self.values]


class ACBPRelation:
    """
    Al-Anazi Categorical-Boolean Paradigm relation.

    A relation declares truth between two categorical dimensions.
    Anything not declared valid becomes invalid under closed-world masking.
    """

    def __init__(
        self,
        left: Dimension,
        right: Dimension,
        valid_pairs: Iterable[Tuple[str, str]],
        name: str = "ACBP Relation",
    ):
        self.left = left
        self.right = right
        self.name = name
        self.valid_pairs = set(valid_pairs)
        self._validate_pairs()

    def _validate_pairs(self):
        for a, b in self.valid_pairs:
            if a not in self.left.values:
                raise ValueError(f"{a!r} is not in left dimension {self.left.name}")
            if b not in self.right.values:
                raise ValueError(f"{b!r} is not in right dimension {self.right.name}")

    def valid_mask(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                [1 if (a, b) in self.valid_pairs else 0 for b in self.right.values]
                for a in self.left.values
            ],
            index=self.left.values,
            columns=self.right.values,
        )

    def invalid_mask(self) -> pd.DataFrame:
        return 1 - self.valid_mask()

    def is_valid(self, left_value: str, right_value: str) -> bool:
        return (left_value, right_value) in self.valid_pairs

    def is_invalid(self, left_value: str, right_value: str) -> bool:
        return not self.is_valid(left_value, right_value)

    def pair_vector(self, left_value: str, right_value: str) -> List[int]:
        """
        Concatenated one-hot declaration:
        [left one-hot | right one-hot]
        """
        return self.left.one_hot(left_value) + self.right.one_hot(right_value)

    def valid_long_table(self) -> pd.DataFrame:
        rows = []
        for a in self.left.values:
            for b in self.right.values:
                rows.append({
                    self.left.name: a,
                    self.right.name: b,
                    "truth": 1 if self.is_valid(a, b) else 0,
                    "state": "VALID" if self.is_valid(a, b) else "INVALID",
                    "vector": "".join(map(str, self.pair_vector(a, b))),
                })
        return pd.DataFrame(rows)

    def invalid_rules(self) -> pd.DataFrame:
        rows = []
        for a in self.left.values:
            invalid_values = [b for b in self.right.values if self.is_invalid(a, b)]
            rows.append({
                self.left.name: a,
                f"invalid_{self.right.name}": ", ".join(invalid_values),
                "invalid_count": len(invalid_values),
            })
        return pd.DataFrame(rows)

    def export_excel(self, path: str):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.valid_mask().to_excel(writer, sheet_name="Valid Mask")
            self.invalid_mask().to_excel(writer, sheet_name="Invalid Mask")
            self.valid_long_table().to_excel(writer, sheet_name="Truth Table", index=False)
            self.invalid_rules().to_excel(writer, sheet_name="Invalid Rules", index=False)
