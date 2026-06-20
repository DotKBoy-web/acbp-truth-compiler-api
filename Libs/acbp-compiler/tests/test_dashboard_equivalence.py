import pandas as pd

from acbp_compiler import (
    compare_dashboard_results,
    dashboard_result_hash,
    latency_comparison,
)


def test_dashboard_hash_equal_after_row_reordering():
    live = pd.DataFrame({
        "unit": ["A", "B"],
        "live_census": [10, 20],
        "capacity": [15, 25],
    })

    cbp = pd.DataFrame({
        "capacity": [25, 15],
        "live_census": [20, 10],
        "unit": ["B", "A"],
    })

    assert dashboard_result_hash(live, key_cols=["unit"]) == dashboard_result_hash(cbp, key_cols=["unit"])


def test_dashboard_comparison_detects_equivalence():
    live = pd.DataFrame({
        "unit": ["A", "B"],
        "live_census": [10, 20],
        "capacity": [15, 25],
        "refreshed_at": ["now1", "now1"],
    })

    cbp = pd.DataFrame({
        "unit": ["B", "A"],
        "live_census": [20, 10],
        "capacity": [25, 15],
        "refreshed_at": ["now2", "now2"],
    })

    result = compare_dashboard_results(
        live,
        cbp,
        key_cols=["unit"],
        ignore_cols=["refreshed_at"],
    )

    assert result["semantic_equivalence"] is True
    assert result["hash_match"] is True
    assert result["row_count_match"] is True


def test_dashboard_comparison_detects_metric_delta():
    live = pd.DataFrame({
        "unit": ["A", "B"],
        "live_census": [10, 20],
    })

    cbp = pd.DataFrame({
        "unit": ["A", "B"],
        "live_census": [10, 22],
    })

    result = compare_dashboard_results(
        live,
        cbp,
        key_cols=["unit"],
        tolerance=0.000001,
    )

    assert result["semantic_equivalence"] is False
    assert result["numeric_match"] is False
    assert result["numeric_deltas"][0]["max_abs_delta"] == 2


def test_latency_comparison_reports_speedup():
    result = latency_comparison(live_ms=1000, cbp_ms=100)

    assert result["faster_path"] == "cbp"
    assert result["speedup_factor"] == 10
