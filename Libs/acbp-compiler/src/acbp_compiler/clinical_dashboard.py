from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from math import prod


FAC01_IPD_DASHBOARD_SPEC: dict[str, Any] = {
    "spec_name": "fac01_ipd_clinical_dashboard",
    "source_repo": "https://github.com/DotKBoy-web/acbp-clinical-dashboard-experiment",
    "description": (
        "Clinical inpatient operational dashboard spec comparing Live SQL execution "
        "against compiled CBP/ACBP dashboard-state execution."
    ),
    "scope": {
        "facility_key": "FAC_01",
        "building_type": "IPD",
        "grain": "encounter_location_day_state",
    },
    "live_sql": {
        "folder": "03_live_query_model/sql",
        "files": [
            "live_base_encounter.sql",
            "live_capacity_logic.sql",
            "live_census_logic.sql",
            "live_dashboard_explain.sql",
            "live_dashboard_query.sql",
        ],
        "execution_mode": "live_sql",
        "meaning": (
            "Dashboard KPIs are computed directly from base encounter, location, "
            "capacity, admission, discharge, and order logic at query time."
        ),
    },
    "cbp_sql": {
        "folder": "04_cbp_model/sql",
        "files": [
            "cbp_dashboard_explain.sql",
            "cbp_dashboard_query.sql",
            "cbp_materialized_view.sql",
            "cbp_refresh_procedure.sql",
        ],
        "execution_mode": "compiled_cbp",
        "meaning": (
            "Dashboard KPIs are served from a compiled categorical-Boolean state layer "
            "with refresh/materialized-view support."
        ),
    },
    "state_definition": {
        "model_name": "fac01_ipd",
        "flags": [
            "f_admit_today",
            "f_disch_today",
            "f_census_live",
            "f_bedded_census_live",
            "f_has_discharge_order",
        ],
        "categories": {
            "facility_key": ["FAC_01"],
            "building_type": ["IPD"],
            "loc_nurse_unit_cd": "ENUM_FROM_DB",
            "loc_room_cd": "ENUM_FROM_DB",
            "loc_bed_cd": "ENUM_FROM_DB",
        },
        "constraints": [
            {
                "type": "IMPLIES",
                "if": "f_bedded_census_live",
                "then": "f_census_live",
            },
            {
                "type": "FORBID_WHEN",
                "flag": "f_bedded_census_live",
                "category_condition": "loc_room_cd IS NULL OR loc_bed_cd IS NULL",
            },
            {
                "type": "FORBID_IF_SQL",
                "flag": "f_disch_today",
                "sql_predicate": "disch_dt_tm < inpatient_admit_dt_tm",
            },
            {
                "type": "IMPLIES",
                "if": "f_has_discharge_order",
                "then": "f_census_live",
            },
        ],
    },
    "dashboard_metrics": [
        "live_census",
        "bedded_census",
        "today_admissions",
        "today_discharges",
        "discharge_orders",
        "capacity",
        "occupancy_rate",
    ],
}


@dataclass
class ClinicalDashboardCompileArtifact:
    spec_name: str
    model_name: str
    execution_modes: list[str]
    flags: list[str]
    categories: dict[str, Any]
    constraints: list[dict[str, Any]]
    metrics: list[str]
    estimated_boolean_state_space: int
    validation: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "spec_name": self.spec_name,
            "model_name": self.model_name,
            "execution_modes": self.execution_modes,
            "flags": self.flags,
            "categories": self.categories,
            "constraints": self.constraints,
            "metrics": self.metrics,
            "estimated_boolean_state_space": self.estimated_boolean_state_space,
            "validation": self.validation,
        }

    def deterministic_brief(self) -> str:
        constraints = "\n".join(
            f"- {c.get('type')}: {c}" for c in self.constraints
        )

        return f"""ACBP Clinical Dashboard Compiler Brief

Spec: {self.spec_name}
Model: {self.model_name}
Execution modes: {", ".join(self.execution_modes)}

Clinical dashboard state:
Flags: {", ".join(self.flags)}
Categories: {", ".join(self.categories.keys())}
Metrics: {", ".join(self.metrics)}

Boolean state-space estimate:
2 ^ {len(self.flags)} = {self.estimated_boolean_state_space}

Constraints:
{constraints}

Meaning:
Live SQL computes dashboard metrics directly from operational tables at query time.
Compiled CBP/ACBP computes or refreshes declared dashboard states first, then serves dashboard metrics from the compiled state layer.

Guardrails:
This spec models operational dashboard state logic.
It is not a patient diagnosis model.
Declared valid states are operational truth declarations, not prediction correctness.
"""


def clinical_dashboard_spec() -> dict[str, Any]:
    return FAC01_IPD_DASHBOARD_SPEC.copy()


def compile_clinical_dashboard_spec(
    spec: dict[str, Any] | None = None,
) -> ClinicalDashboardCompileArtifact:
    spec = spec or FAC01_IPD_DASHBOARD_SPEC

    state = spec["state_definition"]
    flags = list(state["flags"])
    categories = dict(state["categories"])
    constraints = list(state["constraints"])

    estimated_boolean_state_space = int(2 ** len(flags))

    validation = validate_clinical_dashboard_spec(spec)

    return ClinicalDashboardCompileArtifact(
        spec_name=str(spec["spec_name"]),
        model_name=str(state["model_name"]),
        execution_modes=[
            spec["live_sql"]["execution_mode"],
            spec["cbp_sql"]["execution_mode"],
        ],
        flags=flags,
        categories=categories,
        constraints=constraints,
        metrics=list(spec["dashboard_metrics"]),
        estimated_boolean_state_space=estimated_boolean_state_space,
        validation=validation,
    )


def validate_clinical_dashboard_spec(spec: dict[str, Any]) -> dict[str, Any]:
    state = spec["state_definition"]
    flags = set(state.get("flags", []))
    constraints = state.get("constraints", [])

    errors: list[str] = []
    warnings: list[str] = []

    for constraint in constraints:
        ctype = constraint.get("type")

        if ctype == "IMPLIES":
            left = constraint.get("if")
            right = constraint.get("then")

            if left not in flags:
                errors.append(f"IMPLIES uses unknown source flag: {left}")

            if right not in flags:
                errors.append(f"IMPLIES uses unknown target flag: {right}")

        if ctype in {"FORBID_WHEN", "FORBID_IF_SQL"}:
            flag = constraint.get("flag")

            if flag not in flags:
                errors.append(f"{ctype} uses unknown flag: {flag}")

    live_files = spec.get("live_sql", {}).get("files", [])
    cbp_files = spec.get("cbp_sql", {}).get("files", [])

    if not any("dashboard_query" in f for f in live_files):
        warnings.append("Live SQL dashboard query file not declared.")

    if not any("dashboard_query" in f for f in cbp_files):
        warnings.append("CBP dashboard query file not declared.")

    if not any("materialized" in f for f in cbp_files):
        warnings.append("CBP materialized-view file not declared.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "live_sql_files": live_files,
        "cbp_sql_files": cbp_files,
    }


def compare_live_sql_and_cbp_paths(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or FAC01_IPD_DASHBOARD_SPEC

    live = spec["live_sql"]
    cbp = spec["cbp_sql"]

    return {
        "same_dashboard_scope": spec["scope"],
        "live_sql": {
            "mode": live["execution_mode"],
            "folder": live["folder"],
            "files": live["files"],
            "meaning": live["meaning"],
        },
        "cbp_sql": {
            "mode": cbp["execution_mode"],
            "folder": cbp["folder"],
            "files": cbp["files"],
            "meaning": cbp["meaning"],
        },
        "semantic_equivalence_target": (
            "Both paths should return the same dashboard metrics for the same refresh/query window; "
            "differences should be measured as latency, freshness, and deterministic result hash agreement."
        ),
    }
