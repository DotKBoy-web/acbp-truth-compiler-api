import pandas as pd


class ACBPRepairEngine:
    """
    Repair layer for ACBP.

    Given a partial or full invalid declaration, it finds the nearest declared valid truth(s)
    and explains what must change.
    """

    def __init__(self, relation):
        self.relation = relation
        self.dimensions = relation.dimensions
        self.dimension_names = [d.name for d in self.dimensions]

    def _tuple_to_dict(self, values):
        return {dim.name: value for dim, value in zip(self.dimensions, values)}

    def _validate_partial(self, partial):
        dim_map = {d.name: d for d in self.dimensions}

        for key, value in partial.items():
            if key not in dim_map:
                raise ValueError(f"Unknown dimension {key!r}")

            if value not in dim_map[key].values:
                raise ValueError(f"{value!r} is not declared in dimension {key!r}")

    def _changes_from_partial(self, partial, candidate_dict):
        changes = []

        for key, old_value in partial.items():
            new_value = candidate_dict[key]
            if old_value != new_value:
                changes.append(f"{key}: {old_value} -> {new_value}")

        return changes

    def nearest_valid(self, partial, max_results=10):
        self._validate_partial(partial)

        rows = []

        for valid_tuple in sorted(self.relation.valid_tuples):
            candidate = self._tuple_to_dict(valid_tuple)

            compared = 0
            matched = 0
            changed = 0

            for key, value in partial.items():
                compared += 1
                if candidate[key] == value:
                    matched += 1
                else:
                    changed += 1

            changes = self._changes_from_partial(partial, candidate)

            row = dict(candidate)
            row["distance"] = changed
            row["matched_declarations"] = matched
            row["compared_declarations"] = compared
            row["repair_action"] = "; ".join(changes) if changes else "Already valid"
            row["vector"] = "".join(map(str, self.relation.tuple_vector(valid_tuple)))
            rows.append(row)

        df = pd.DataFrame(rows)

        return (
            df.sort_values(["distance", "matched_declarations"], ascending=[True, False])
            .head(max_results)
            .reset_index(drop=True)
        )

    def contradiction_report(self, partial, max_results=10):
        from .query import ACBPQueryEngine

        query = ACBPQueryEngine(self.relation)
        valid = query.valid_given(partial)

        if not valid.empty:
            status = "SATISFIABLE"
            nearest = valid.copy()
            nearest["distance"] = 0
            nearest["repair_action"] = "Already valid"
            return status, nearest

        status = "CONTRADICTION"
        nearest = self.nearest_valid(partial, max_results=max_results)
        return status, nearest

    def export_repair_report(self, path, test_cases):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.relation.truth_table().to_excel(writer, sheet_name="Truth Space", index=False)
            self.relation.valid_table().to_excel(writer, sheet_name="Declared Valid", index=False)

            summary_rows = []

            for i, case in enumerate(test_cases, start=1):
                status, repairs = self.contradiction_report(case)
                repairs.to_excel(writer, sheet_name=f"Case {i} Repairs", index=False)

                summary_rows.append({
                    "case_no": i,
                    "declaration": str(case),
                    "status": status,
                    "best_distance": None if repairs.empty else int(repairs.iloc[0]["distance"]),
                    "best_repair": None if repairs.empty else repairs.iloc[0]["repair_action"],
                })

            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Repair Summary", index=False)
