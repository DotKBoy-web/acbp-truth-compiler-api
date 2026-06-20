from acbp_compiler import ACBPCompilerApiService


def test_api_service_compiles_truth_space():
    service = ACBPCompilerApiService()

    payload = {
        "name": "object_color",
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

    result = service.compile_truth_space(payload)

    assert result["summary"]["truth_space_size"] == 9
    assert result["summary"]["declared_valid_count"] == 6
    assert result["summary"]["derived_invalid_count"] == 3


def test_api_service_compacts_column_stats():
    service = ACBPCompilerApiService()

    result = service.compact_features({
        "target_cardinality": 3,
        "n_rows": 240,
        "columns": [
            {"name": "Case_ID", "type": "id", "unique": 240},
            {"name": "Actual_Start", "type": "timestamp", "unique": 180},
            {"name": "Delay_Bucket", "type": "category", "unique": 5},
            {"name": "ASA_Class", "type": "category", "unique": 5},
        ],
        "max_truth_space": 20000,
    })

    selected = result["summary"]["selected_features"]

    assert "Case_ID" not in selected
    assert "Actual_Start" not in selected
    assert "Delay_Bucket" in selected


def test_api_service_compares_dashboard_results():
    service = ACBPCompilerApiService()

    result = service.compare_dashboard({
        "live_sql_result": [
            {"unit": "A", "live_census": 10},
            {"unit": "B", "live_census": 20},
        ],
        "cbp_result": [
            {"unit": "B", "live_census": 20},
            {"unit": "A", "live_census": 10},
        ],
        "key_cols": ["unit"],
    })

    assert result["summary"]["semantic_equivalence"] is True
    assert result["summary"]["hash_match"] is True
