import pandas as pd

from acbp_ml import ACBPDatasetProfiler, ACBPUseCaseAdvisor


def test_dataset_profiler_detects_candidate_target():
    df = pd.DataFrame({
        "age": [10, 20, 30, 40, 50, 60],
        "gender": ["M", "F", "M", "F", "M", "F"],
        "risk": ["low", "low", "high", "high", "low", "high"],
    })

    profile = ACBPDatasetProfiler.profile(df)

    assert profile["n_rows"] == 6
    assert profile["n_columns"] == 3
    assert "risk" in profile["candidate_targets"] or "gender" in profile["candidate_targets"]


def test_recommend_features_excludes_target():
    df = pd.DataFrame({
        "age": [10, 20, 30, 40, 50, 60],
        "score": [1, 2, 3, 4, 5, 6],
        "risk": ["low", "low", "high", "high", "low", "high"],
    })

    features = ACBPDatasetProfiler.recommend_features(df, target_col="risk")

    assert "risk" not in features
    assert len(features) >= 1


def test_usecase_advisor_returns_ranked_table():
    df = pd.DataFrame({
        "age": [10, 20, 30, 40, 50, 60],
        "score": [1, 2, 3, 4, 5, 6],
        "risk": ["low", "low", "high", "high", "low", "high"],
    })

    profile = ACBPDatasetProfiler.profile(df, target_col="risk")
    recs = ACBPUseCaseAdvisor.recommend(profile, target_col="risk")

    assert len(recs) >= 3
    assert "use_case_id" in recs.columns
    assert "score" in recs.columns
