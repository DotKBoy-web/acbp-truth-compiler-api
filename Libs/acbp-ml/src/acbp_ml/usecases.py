from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class ACBPUseCase:
    use_case_id: str
    title: str
    best_for: str
    target_required: bool
    output_focus: str
    example_domains: str
    caution: str


ACBP_USE_CASES = [
    ACBPUseCase(
        "classification_truth_space",
        "Classification Truth-Space Analysis",
        "Datasets with a known target label where you want interpretable class-feature truth tuples.",
        True,
        "Declared valid tuples, derived invalid tuples, prediction explanation, confusion matrix.",
        "Clinical benchmarks, quality categories, risk groups, operational classes.",
        "Do not present as clinical deployment without validation."
    ),
    ACBPUseCase(
        "data_quality_rules",
        "Data Quality and Validity Rules",
        "Datasets where valid combinations of fields matter more than prediction.",
        True,
        "Invalid combinations, contradiction detection, repair suggestions.",
        "HIS mappings, clinic-resource-service mapping, forms, workflows.",
        "Requires domain-approved declared truths."
    ),
    ACBPUseCase(
        "workflow_compliance",
        "Workflow Compliance and Process State Logic",
        "Processes with states, steps, locations, roles, or statuses.",
        True,
        "Allowed state transitions, impossible states, missing declarations.",
        "OPD flow, appointment status, triage flow, medication workflow.",
        "Must define the process dimensions clearly."
    ),
    ACBPUseCase(
        "mapping_reconciliation",
        "System Mapping Reconciliation",
        "Comparing categories between systems and detecting invalid cross-system mappings.",
        True,
        "Valid mappings, unmapped categories, invalid pairings, mapping repair.",
        "HIS vs queue system, Cerner resources, clinic/service mapping.",
        "Garbage mappings create garbage truth."
    ),
    ACBPUseCase(
        "risk_policy_audit",
        "Risk Policy Audit",
        "When a model has a risk class and you need transparent policy movement.",
        True,
        "Missed risk cases, false alarms, policy tradeoff, transition audit.",
        "Cancer benchmark, patient risk category, operational escalation.",
        "Policy tuning is not the same as clinical validation."
    ),
    ACBPUseCase(
        "explainability_layer",
        "Explainability Layer Beside ML",
        "When you need symbolic explanation beside a black-box or statistical model.",
        True,
        "Nearest declared truth, exact support, candidate scores, contradiction.",
        "Random forest comparison, dashboard explanation, governance review.",
        "Explanation depends on quality of declared truth space."
    ),
]


class ACBPUseCaseAdvisor:
    @staticmethod
    def table() -> pd.DataFrame:
        return pd.DataFrame([u.__dict__ for u in ACBP_USE_CASES])

    @staticmethod
    def recommend(profile: dict, target_col: str | None = None) -> pd.DataFrame:
        rows = []
        n_rows = int(profile.get("n_rows", 0))
        n_columns = int(profile.get("n_columns", 0))
        candidate_targets = profile.get("candidate_targets", [])

        has_target = target_col is not None and target_col != ""
        many_columns = n_columns >= 6
        enough_rows = n_rows >= 50

        for use_case in ACBP_USE_CASES:
            score = 0
            reasons = []

            if use_case.target_required and has_target:
                score += 3
                reasons.append("Target selected.")
            elif use_case.target_required and candidate_targets:
                score += 1
                reasons.append("Candidate target columns detected.")
            elif use_case.target_required:
                score -= 2
                reasons.append("Needs a target/state column.")

            if enough_rows:
                score += 1
                reasons.append("Enough rows for train/test analysis.")
            else:
                reasons.append("Small dataset; better for rule/mapping analysis.")

            if many_columns and use_case.use_case_id in ["classification_truth_space", "explainability_layer", "risk_policy_audit"]:
                score += 1
                reasons.append("Multiple dimensions available.")

            if use_case.use_case_id in ["data_quality_rules", "mapping_reconciliation", "workflow_compliance"]:
                score += 1
                reasons.append("ACBP naturally fits declared validity and invalid combinations.")

            if use_case.use_case_id == "risk_policy_audit" and has_target:
                score += 1
                reasons.append("Risk class can be selected from target values.")

            rows.append({
                "use_case_id": use_case.use_case_id,
                "title": use_case.title,
                "score": score,
                "reason": " ".join(reasons),
                "best_for": use_case.best_for,
                "output_focus": use_case.output_focus,
                "caution": use_case.caution,
            })

        out = pd.DataFrame(rows)
        return out.sort_values(["score", "title"], ascending=[False, True]).reset_index(drop=True)

    @staticmethod
    def get(use_case_id: str) -> ACBPUseCase:
        for u in ACBP_USE_CASES:
            if u.use_case_id == use_case_id:
                return u
        raise KeyError(f"Unknown ACBP use case: {use_case_id}")
