import pandas as pd


class ACBPPolicyRepairEngine:
    """
    Policy-aware repair layer for ACBP.

    Adds:
    - locked dimensions: dimensions that must not change
    - dimension weights: changing some dimensions costs more than others
    - ranked repair suggestions
    """

    def __init__(self, relation, locked_dimensions=None, weights=None):
        self.relation = relation
        self.dimensions = relation.dimensions
        self.dimension_names = [d.name for d in self.dimensions]
        self.locked_dimensions = set(locked_dimensions or [])
        self.weights = weights or {}

        for d in self.locked_dimensions:
            if d not in self.dimension_names:
                raise ValueError(f"Unknown locked dimension: {d}")

    def _tuple_to_dict(self, values):
        return {dim.name: value for dim, value in zip(self.dimensions, values)}

    def _validate_partial(self, partial):
        dim_map = {d.name: d for d in self.dimensions}

        for key, value in partial.items():
            if key not in dim_map:
                raise ValueError(f"Unknown dimension {key!r}")

            if value not in dim_map[key].values:
                raise ValueError(f"{value!r} is not declared in dimension {key!r}")

    def _change_cost(self, dimension_name):
        return float(self.weights.get(dimension_name, 1.0))

    def nearest_valid(self, partial, max_results=10):
        self._validate_partial(partial)

        rows = []

        for valid_tuple in sorted(self.relation.valid_tuples):
            candidate = self._tuple_to_dict(valid_tuple)

            # Locked dimensions cannot change if declared in the partial input
            violates_lock = False
            for locked in self.locked_dimensions:
                if locked in partial and candidate[locked] != partial[locked]:
                    violates_lock = True
                    break

            if violates_lock:
                continue

            changes = []
            matched = 0
            changed = 0
            weighted_distance = 0.0

            for key, old_value in partial.items():
                new_value = candidate[key]

                if old_value == new_value:
                    matched += 1
                else:
                    changed += 1
                    cost = self._change_cost(key)
                    weighted_distance += cost
                    changes.append(f"{key}: {old_value} -> {new_value} (cost={cost})")

            row = dict(candidate)
            row["raw_distance"] = changed
            row["weighted_distance"] = weighted_distance
            row["matched_declarations"] = matched
            row["locked_dimensions"] = ", ".join(sorted(self.locked_dimensions)) if self.locked_dimensions else ""
            row["repair_action"] = "; ".join(changes) if changes else "Already valid"
            row["vector"] = "".join(map(str, self.relation.tuple_vector(valid_tuple)))
            rows.append(row)

        if not rows:
            return pd.DataFrame(columns=[
                *self.dimension_names,
                "raw_distance",
                "weighted_distance",
                "matched_declarations",
                "locked_dimensions",
                "repair_action",
                "vector",
            ])

        df = pd.DataFrame(rows)

        return (
            df.sort_values(
                ["weighted_distance", "raw_distance", "matched_declarations"],
                ascending=[True, True, False],
            )
            .head(max_results)
            .reset_index(drop=True)
        )

    def report(self, partial, max_results=10):
        from .query import ACBPQueryEngine

        q = ACBPQueryEngine(self.relation)
        valid = q.valid_given(partial)

        if not valid.empty:
            valid = valid.copy()
            valid["raw_distance"] = 0
            valid["weighted_distance"] = 0.0
            valid["repair_action"] = "Already valid"
            return "SATISFIABLE", valid

        repairs = self.nearest_valid(partial, max_results=max_results)

        if repairs.empty:
            return "CONTRADICTION_NO_REPAIR_UNDER_POLICY", repairs

        return "CONTRADICTION_REPAIRABLE", repairs

    def export_policy_report(self, path, cases):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.relation.truth_table().to_excel(writer, sheet_name="Truth Space", index=False)
            self.relation.valid_table().to_excel(writer, sheet_name="Declared Valid", index=False)

            summary = []

            for i, case in enumerate(cases, start=1):
                status, repairs = self.report(case)
                repairs.to_excel(writer, sheet_name=f"Case {i}", index=False)

                summary.append({
                    "case_no": i,
                    "declaration": str(case),
                    "status": status,
                    "best_weighted_distance": None if repairs.empty else repairs.iloc[0]["weighted_distance"],
                    "best_repair": None if repairs.empty else repairs.iloc[0]["repair_action"],
                })

            pd.DataFrame(summary).to_excel(writer, sheet_name="Policy Summary", index=False)
