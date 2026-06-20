import pandas as pd

from acbp_compiler import ACBPCompilerOptions, ACBPCompilerProductService


def test_product_service_compiles_clinical_dashboard(tmp_path):
    service = ACBPCompilerProductService(product_home=tmp_path)

    result = service.compile_clinical_dashboard()

    assert result["summary"]["model_name"] == "fac01_ipd"
    assert result["project_id"]
    assert result["export_url"]

    zip_path = service.export_project_zip(result["project_id"])
    assert zip_path.exists()


def test_product_service_compiles_dataset_file(tmp_path):
    df = pd.DataFrame({
        "Case_ID": ["C1", "C2", "C3", "C4"],
        "Delay_Bucket": ["0-15", "0-15", ">90", ">90"],
        "Case_Priority": ["Elective", "Elective", "Emergency", "Urgent"],
        "OR_Risk_Class": ["LowRisk", "LowRisk", "HighRiskDelay", "ModerateRisk"],
    })

    data_path = tmp_path / "or.csv"
    df.to_csv(data_path, index=False)

    service = ACBPCompilerProductService(product_home=tmp_path / "projects")

    result = service.compile_dataset_file(
        path=data_path,
        original_name="or.csv",
        target_col="OR_Risk_Class",
        risk_class="HighRiskDelay",
        options=ACBPCompilerOptions(auto_compact=True, max_truth_space=1000),
    )

    assert result["summary"]["target_col"] == "OR_Risk_Class"
    assert result["project_id"]
    assert service.get_project(result["project_id"])["summary"]["target_col"] == "OR_Risk_Class"


def test_product_service_compares_dashboard_files(tmp_path):
    live = pd.DataFrame({
        "unit": ["A", "B"],
        "live_census": [10, 20],
    })

    cbp = pd.DataFrame({
        "unit": ["B", "A"],
        "live_census": [20, 10],
    })

    live_path = tmp_path / "live.csv"
    cbp_path = tmp_path / "cbp.csv"

    live.to_csv(live_path, index=False)
    cbp.to_csv(cbp_path, index=False)

    service = ACBPCompilerProductService(product_home=tmp_path / "projects")

    result = service.compare_dashboard_files(
        live_path=live_path,
        cbp_path=cbp_path,
        key_cols=["unit"],
    )

    assert result["summary"]["semantic_equivalence"] is True
    assert result["project_id"]
