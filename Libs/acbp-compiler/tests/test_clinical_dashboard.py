from acbp_compiler import (
    FAC01_IPD_DASHBOARD_SPEC,
    compile_clinical_dashboard_spec,
    compare_live_sql_and_cbp_paths,
    validate_clinical_dashboard_spec,
)


def test_clinical_dashboard_spec_compiles():
    artifact = compile_clinical_dashboard_spec()

    assert artifact.model_name == "fac01_ipd"
    assert "live_sql" in artifact.execution_modes
    assert "compiled_cbp" in artifact.execution_modes
    assert "f_census_live" in artifact.flags
    assert "f_bedded_census_live" in artifact.flags
    assert artifact.estimated_boolean_state_space == 32
    assert artifact.validation["ok"] is True


def test_clinical_dashboard_constraints_reference_known_flags():
    result = validate_clinical_dashboard_spec(FAC01_IPD_DASHBOARD_SPEC)

    assert result["ok"] is True
    assert result["errors"] == []


def test_compare_live_sql_and_cbp_paths_declares_both_query_paths():
    result = compare_live_sql_and_cbp_paths()

    live_files = result["live_sql"]["files"]
    cbp_files = result["cbp_sql"]["files"]

    assert "live_dashboard_query.sql" in live_files
    assert "cbp_dashboard_query.sql" in cbp_files
    assert "cbp_materialized_view.sql" in cbp_files
    assert result["same_dashboard_scope"]["facility_key"] == "FAC_01"
    assert result["same_dashboard_scope"]["building_type"] == "IPD"
