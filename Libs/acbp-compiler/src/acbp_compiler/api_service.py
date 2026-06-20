from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from acbp_ml import auto_compact_features

from .clinical_dashboard import compile_clinical_dashboard_spec
from .compiler import compile_truth_spec
from .dashboard_equivalence import compare_dashboard_results
from .product_service import ACBPCompilerProductService


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]

    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass

    return obj


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _split_features(value: Any) -> list[str] | None:
    if value is None:
        return None

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    return [x.strip() for x in str(value).split(",") if x.strip()] or None


def _name_bonus(name: str) -> float:
    n = name.lower()
    bonus = 0.0

    if "bucket" in n:
        bonus += 1.10
    if "flag" in n:
        bonus += 0.60
    if "priority" in n:
        bonus += 0.55
    if "asa" in n:
        bonus += 0.50
    if "class" in n:
        bonus += 0.35
    if "type" in n:
        bonus += 0.25
    if "group" in n:
        bonus += 0.20
    if "service" in n:
        bonus += 0.15

    return bonus


def _column_reject_reason(name: str, col_type: str | None = None) -> str | None:
    n = name.lower().strip()
    t = str(col_type or "").lower().strip()

    if n in {"id", "case_id", "patient_id", "encounter_id", "mrn"}:
        return "Identifier column; creates memorization rather than reusable truth."

    if n.endswith("_id"):
        return "Identifier-like column; creates memorization rather than reusable truth."

    if any(x in n for x in ["name", "date", "time", "timestamp", "created", "updated"]):
        return "Name/date/time-like column; not suitable for compact declared-truth modeling."

    if any(x in n for x in ["_min", "minutes", "duration_min", "delay_min", "turnover_min"]):
        return "Raw continuous measurement; prefer a bucketed categorical version."

    if t in {"id", "identifier", "datetime", "timestamp"}:
        return f"Column type '{t}' is not suitable for compact declared-truth modeling."

    return None


@dataclass
class ACBPCompilerApiService:
    product_service: ACBPCompilerProductService | None = None

    def compile_truth_space(
        self,
        payload: dict[str, Any],
        save_artifact: bool = False,
    ) -> dict[str, Any]:
        artifact = compile_truth_spec(payload)

        result = {
            "api_version": "v1",
            "artifact_type": "declared_truth_model",
            "summary": artifact.summary(),
            "brief": artifact.deterministic_brief(),
            "guardrails": [
                "Truth space is not the confusion matrix.",
                "Declared valid count is not prediction correctness.",
                "Derived invalid count is not model error.",
            ],
        }

        if save_artifact and self.product_service:
            result.update(
                self.product_service.save_artifact_pack(
                    kind="api_truth_space_compile",
                    title=artifact.name,
                    payload=result,
                )
            )

        return _json_safe(result)

    def compact_features(
        self,
        payload: dict[str, Any],
        save_artifact: bool = False,
    ) -> dict[str, Any]:
        records = payload.get("records")

        if records:
            result = self._compact_from_records(payload)
        else:
            result = self._compact_from_column_stats(payload)

        response = {
            "api_version": "v1",
            "artifact_type": "compact_feature_recommendation",
            "summary": result,
            "brief": self._compact_brief(result),
            "guardrails": [
                "Auto Compact is a truth-space safety recommendation.",
                "It does not prove predictive accuracy.",
                "Identifier, date/time, and raw continuous columns are usually excluded.",
            ],
        }

        if save_artifact and self.product_service:
            response.update(
                self.product_service.save_artifact_pack(
                    kind="api_compact_features",
                    title=str(payload.get("name", "compact_features")),
                    payload=response,
                )
            )

        return _json_safe(response)

    def _compact_from_records(self, payload: dict[str, Any]) -> dict[str, Any]:
        target_col = str(payload.get("target_col", "")).strip()

        if not target_col:
            raise ValueError("target_col is required when records are supplied.")

        df = pd.DataFrame(payload.get("records", []))

        if target_col not in df.columns:
            raise ValueError(f"target_col not found in records: {target_col}")

        return auto_compact_features(
            df=df,
            target_col=target_col,
            candidate_features=_split_features(payload.get("candidate_features")),
            n_bins=int(payload.get("n_bins", 3)),
            max_features=int(payload.get("max_features", 6)),
            max_truth_space=int(payload.get("max_truth_space", 20_000)),
            min_density=float(payload.get("min_density", 0.02)),
        )

    def _compact_from_column_stats(self, payload: dict[str, Any]) -> dict[str, Any]:
        columns = payload.get("columns") or []

        if not isinstance(columns, list) or not columns:
            raise ValueError("Provide either records or columns metadata.")

        target_cardinality = int(payload.get("target_cardinality", 2))
        max_features = int(payload.get("max_features", 6))
        max_truth_space = int(payload.get("max_truth_space", 20_000))
        min_density = float(payload.get("min_density", 0.02))
        n_rows = int(payload.get("n_rows", 1))
        n_bins = int(payload.get("n_bins", 3))

        scored: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []

        for col in columns:
            name = str(col.get("name", "")).strip()

            if not name:
                continue

            col_type = col.get("type")
            reason = _column_reject_reason(name, col_type)

            raw_unique = int(col.get("unique", col.get("cardinality", 1)) or 1)

            if str(col_type or "").lower() in {"number", "numeric", "float", "integer"} and raw_unique > 10:
                cardinality = n_bins
            else:
                cardinality = int(col.get("cardinality", raw_unique) or 1)

            cardinality = max(cardinality, 1)

            if reason:
                excluded.append({
                    "feature": name,
                    "cardinality": cardinality,
                    "excluded": True,
                    "reason": reason,
                })
                continue

            bonus = _name_bonus(name)
            score = bonus - (0.12 * max(cardinality - 2, 0))

            scored.append({
                "feature": name,
                "score": round(score, 6),
                "cardinality": cardinality,
                "name_bonus": round(bonus, 6),
                "excluded": False,
                "reason": f"cardinality={cardinality}, name_bonus={bonus:.2f}",
            })

        scored = sorted(scored, key=lambda x: (x["score"], -x["cardinality"]), reverse=True)

        selected = []
        rejected = []
        truth_space = max(target_cardinality, 1)

        for item in scored:
            proposed = truth_space * int(item["cardinality"])
            density_upper = min(n_rows, proposed) / proposed if proposed else 0.0

            can_add = (
                len(selected) < max_features
                and proposed <= max_truth_space
                and density_upper >= min_density
            )

            if len(selected) < 2 and proposed <= max_truth_space:
                can_add = True

            if can_add:
                selected.append(item)
                truth_space = proposed
            else:
                rejected_item = dict(item)
                rejected_item["rejected_reason"] = (
                    f"Would make truth_space={proposed:,}, density_upper={density_upper:.6f}"
                )
                rejected.append(rejected_item)

        density_upper = min(n_rows, truth_space) / truth_space if truth_space else 0.0

        return {
            "selected_features": [x["feature"] for x in selected],
            "selected_details": selected,
            "rejected_details": rejected,
            "excluded_details": excluded,
            "estimate": {
                "target_cardinality": target_cardinality,
                "n_rows": n_rows,
                "truth_space_size": truth_space,
                "declared_upper_bound": min(n_rows, truth_space),
                "density_upper_bound": density_upper,
                "max_truth_space": max_truth_space,
                "min_density": min_density,
            },
            "advice": "Selected compact dimensions and excluded risky identifier/date/raw-measure columns.",
        }

    def _compact_brief(self, result: dict[str, Any]) -> str:
        selected = result.get("selected_features", [])
        estimate = result.get("estimate", {})

        return f"""ACBP Compact Feature Recommendation

Selected features:
{", ".join(selected) if selected else "None"}

Estimated truth space: {estimate.get("truth_space_size")}
Density upper bound: {estimate.get("density_upper_bound")}

Meaning:
This recommendation reduces truth-space explosion risk before compiling categorical truth models.
"""

    def compare_dashboard(
        self,
        payload: dict[str, Any],
        save_artifact: bool = False,
    ) -> dict[str, Any]:
        live_rows = payload.get("live_sql_result") or payload.get("live_result")
        cbp_rows = payload.get("cbp_result") or payload.get("compiled_result")

        if not isinstance(live_rows, list) or not isinstance(cbp_rows, list):
            raise ValueError("live_sql_result and cbp_result must be lists of row objects.")

        live_df = pd.DataFrame(live_rows)
        cbp_df = pd.DataFrame(cbp_rows)

        result = compare_dashboard_results(
            live_df=live_df,
            cbp_df=cbp_df,
            key_cols=_split_features(payload.get("key_cols")) or [],
            ignore_cols=_split_features(payload.get("ignore_cols")) or [],
            tolerance=float(payload.get("tolerance", 0.000001)),
        )

        response = {
            "api_version": "v1",
            "artifact_type": "dashboard_equivalence_report",
            "summary": result,
            "brief": (
                "ACBP Dashboard Equivalence Report\n\n"
                "Live SQL and compiled CBP dashboard outputs were compared using normalized hashes, "
                "row/column checks, and numeric tolerance."
            ),
        }

        if save_artifact and self.product_service:
            response.update(
                self.product_service.save_artifact_pack(
                    kind="api_dashboard_compare",
                    title=str(payload.get("name", "dashboard_compare")),
                    payload=response,
                )
            )

        return _json_safe(response)

    def clinical_dashboard_spec(
        self,
        save_artifact: bool = False,
    ) -> dict[str, Any]:
        artifact = compile_clinical_dashboard_spec()

        response = {
            "api_version": "v1",
            "artifact_type": "clinical_dashboard_spec",
            "summary": artifact.summary(),
            "brief": artifact.deterministic_brief(),
        }

        if save_artifact and self.product_service:
            response.update(
                self.product_service.save_artifact_pack(
                    kind="api_clinical_dashboard_spec",
                    title=artifact.spec_name,
                    payload=response,
                )
            )

        return _json_safe(response)

