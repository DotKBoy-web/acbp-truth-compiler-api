from typing import Dict, Optional
import pandas as pd


class ACBPQueryEngine:
    """
    Query layer for MultiACBPRelation.

    It supports:
    - partial declarations
    - valid/invalid filtering
    - possible value projection
    - contradiction detection
    - conditional masks
    """

    def __init__(self, relation):
        self.relation = relation

    def _dimension_names(self):
        return [d.name for d in self.relation.dimensions]

    def _validate_partial(self, partial: Dict[str, str]):
        dim_names = self._dimension_names()
        dim_map = {d.name: d for d in self.relation.dimensions}

        for key, value in partial.items():
            if key not in dim_names:
                raise ValueError(f"Unknown dimension {key!r}. Valid dimensions: {dim_names}")

            if value not in dim_map[key].values:
                raise ValueError(f"{value!r} is not declared in dimension {key!r}")

    def filter_table(self, partial: Optional[Dict[str, str]] = None, state: Optional[str] = None) -> pd.DataFrame:
        partial = partial or {}
        self._validate_partial(partial)

        df = self.relation.truth_table()

        for key, value in partial.items():
            df = df[df[key] == value]

        if state is not None:
            state = state.upper()
            df = df[df["state"] == state]

        return df.reset_index(drop=True)

    def valid_given(self, partial: Dict[str, str]) -> pd.DataFrame:
        return self.filter_table(partial, state="VALID")

    def invalid_given(self, partial: Dict[str, str]) -> pd.DataFrame:
        return self.filter_table(partial, state="INVALID")

    def is_contradiction(self, partial: Dict[str, str]) -> bool:
        return len(self.valid_given(partial)) == 0

    def possible_values(self, partial: Dict[str, str], target_dimension: str) -> pd.DataFrame:
        if target_dimension not in self._dimension_names():
            raise ValueError(f"Unknown target dimension {target_dimension!r}")

        valid = self.valid_given(partial)

        if valid.empty:
            return pd.DataFrame(columns=[target_dimension, "valid_count"])

        return (
            valid.groupby(target_dimension)
            .size()
            .reset_index(name="valid_count")
            .sort_values(["valid_count", target_dimension], ascending=[False, True])
            .reset_index(drop=True)
        )

    def explain(self, partial: Dict[str, str]) -> pd.DataFrame:
        valid = self.valid_given(partial)
        invalid = self.invalid_given(partial)

        conclusion = "CONTRADICTION" if valid.empty else "SATISFIABLE"

        return pd.DataFrame([{
            "partial_declaration": str(partial),
            "valid_matches": len(valid),
            "invalid_matches": len(invalid),
            "conclusion": conclusion,
        }])

    def conditional_mask(
        self,
        row_dimension: str,
        column_dimension: str,
        fixed: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        fixed = fixed or {}
        self._validate_partial(fixed)

        dim_map = {d.name: d for d in self.relation.dimensions}

        if row_dimension not in dim_map:
            raise ValueError(f"Unknown row dimension: {row_dimension}")

        if column_dimension not in dim_map:
            raise ValueError(f"Unknown column dimension: {column_dimension}")

        rows = dim_map[row_dimension].values
        cols = dim_map[column_dimension].values

        matrix = []

        for r in rows:
            line = []
            for c in cols:
                partial = dict(fixed)
                partial[row_dimension] = r
                partial[column_dimension] = c
                line.append(1 if len(self.valid_given(partial)) > 0 else 0)
            matrix.append(line)

        return pd.DataFrame(matrix, index=rows, columns=cols)

    def export_query_report(self, path: str, partial_queries: list):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.relation.truth_table().to_excel(writer, sheet_name="Truth Space", index=False)
            self.relation.valid_table().to_excel(writer, sheet_name="Declared Valid", index=False)
            self.relation.invalid_table().to_excel(writer, sheet_name="Derived Invalid", index=False)

            explanations = []
            for i, q in enumerate(partial_queries, start=1):
                self.valid_given(q).to_excel(writer, sheet_name=f"Q{i} Valid", index=False)
                self.invalid_given(q).to_excel(writer, sheet_name=f"Q{i} Invalid", index=False)
                explanations.append(self.explain(q))

            pd.concat(explanations, ignore_index=True).to_excel(writer, sheet_name="Query Summary", index=False)
