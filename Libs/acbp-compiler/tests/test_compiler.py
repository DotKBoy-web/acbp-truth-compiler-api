import pandas as pd

from acbp_compiler import (
    ACBPCompilerOptions,
    compile_dataframe,
    compile_truth_spec,
    enumerate_invalid_sample,
)


def test_compile_truth_spec_object_color():
    spec = {
        "name": "Object color truth spec",
        "target_col": "Object",
        "risk_class": None,
        "dimensions": [
            {"name": "TargetClass", "values": ["Apple", "Banana", "Mango"]},
            {"name": "Color", "values": ["Red", "Yellow", "Green"]},
        ],
        "declared_truths": [
            {"TargetClass": "Apple", "Color": "Red"},
            {"TargetClass": "Apple", "Color": "Green"},
            {"TargetClass": "Banana", "Color": "Yellow"},
            {"TargetClass": "Banana", "Color": "Green"},
            {"TargetClass": "Mango", "Color": "Red"},
            {"TargetClass": "Mango", "Color": "Yellow"},
        ],
    }

    artifact = compile_truth_spec(spec)

    assert artifact.truth_space_size == 9
    assert artifact.declared_valid_count == 6
    assert artifact.derived_invalid_count == 3
    assert round(artifact.truth_density, 4) == round(6 / 9, 4)


def test_compile_dataframe_with_auto_compact_rejects_id_columns():
    df = pd.DataFrame({
        "Case_ID": [f"C{i}" for i in range(80)],
        "Actual_Start": [f"08:{i % 60:02d}" for i in range(80)],
        "Delay_Bucket": ["0-15 min"] * 20 + ["16-45 min"] * 20 + ["46-90 min"] * 20 + [">90 min"] * 20,
        "Case_Priority": ["Elective"] * 40 + ["Urgent"] * 20 + ["Emergency"] * 20,
        "ASA_Class": ["ASA I", "ASA II", "ASA III", "ASA IV"] * 20,
        "OR_Risk_Class": ["LowRisk"] * 35 + ["ModerateRisk"] * 25 + ["HighRiskDelay"] * 20,
    })

    artifact = compile_dataframe(
        df=df,
        target_col="OR_Risk_Class",
        risk_class="HighRiskDelay",
        options=ACBPCompilerOptions(
            auto_compact=True,
            max_features=5,
            max_truth_space=20_000,
            min_density=0.02,
        ),
    )

    assert "Case_ID" not in artifact.features
    assert "Actual_Start" not in artifact.features
    assert "Delay_Bucket" in artifact.features
    assert artifact.truth_space_size <= 20_000
    assert artifact.declared_valid_count > 0


def test_invalid_sample_does_not_materialize_full_table():
    spec = {
        "name": "Tiny spec",
        "dimensions": [
            {"name": "TargetClass", "values": ["A", "B"]},
            {"name": "X", "values": ["x1", "x2", "x3"]},
        ],
        "declared_truths": [
            {"TargetClass": "A", "X": "x1"},
        ],
    }

    artifact = compile_truth_spec(spec)
    sample = enumerate_invalid_sample(artifact, limit=2)

    assert len(sample) == 2
    assert all(row["state"] == "INVALID" for row in sample)
