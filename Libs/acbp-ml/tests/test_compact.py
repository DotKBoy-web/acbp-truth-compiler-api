import pandas as pd

from acbp_ml import ACBPCompactFeatureSelector, auto_compact_features


def test_auto_compact_rejects_identifier_and_time_columns():
    df = pd.DataFrame({
        "Case_ID": [f"C{i}" for i in range(50)],
        "Actual_Start": [f"08:{i:02d}" for i in range(50)],
        "Delay_Bucket": ["0-15 min"] * 20 + ["46-90 min"] * 15 + [">90 min"] * 15,
        "Case_Priority": ["Elective"] * 25 + ["Urgent"] * 15 + ["Emergency"] * 10,
        "ASA_Class": ["ASA II", "ASA III", "ASA II", "ASA IV", "ASA I"] * 10,
        "OR_Risk_Class": ["LowRisk"] * 25 + ["ModerateRisk"] * 15 + ["HighRiskDelay"] * 10,
    })

    result = auto_compact_features(
        df=df,
        target_col="OR_Risk_Class",
        candidate_features=["Case_ID", "Actual_Start", "Delay_Bucket", "Case_Priority", "ASA_Class"],
        max_truth_space=20_000,
        min_density=0.02,
    )

    assert "Case_ID" not in result["selected_features"]
    assert "Actual_Start" not in result["selected_features"]
    assert "Delay_Bucket" in result["selected_features"]
    assert result["estimate"]["truth_space_size"] <= 20_000
    assert result["excluded_details"]


def test_compact_selector_keeps_truth_space_under_limit():
    df = pd.DataFrame({
        "Delay_Bucket": ["0-15 min", "16-45 min", "46-90 min", ">90 min"] * 20,
        "Duration_Bucket": ["<=60 min", "61-120 min", "121-180 min", ">180 min"] * 20,
        "Turnover_Bucket": ["<=20 min", "21-40 min", "41-60 min", ">60 min"] * 20,
        "Case_Priority": ["Elective", "Urgent", "Emergency", "Elective"] * 20,
        "ASA_Class": ["ASA I", "ASA II", "ASA III", "ASA IV"] * 20,
        "OR_Risk_Class": ["LowRisk", "ModerateRisk", "HighRiskDelay", "ModerateRisk"] * 20,
    })

    selector = ACBPCompactFeatureSelector(max_features=5, max_truth_space=10_000, min_density=0.02)
    result = selector.select(df, target_col="OR_Risk_Class")

    assert len(result["selected_features"]) <= 5
    assert result["estimate"]["truth_space_size"] <= 10_000
    assert result["selected_features"]
