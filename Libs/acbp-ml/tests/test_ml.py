import pandas as pd

from acbp_ml import ACBPClassifier, ACBPSmoothRiskPolicy


def test_acbp_classifier_separable_object_features():
    X = pd.DataFrame({
        "Color": ["Red", "Green", "Yellow", "Green", "Red", "Yellow"],
        "Shape": ["Round", "Round", "Long", "Long", "Oval", "Oval"],
    })

    y = pd.Series(["Apple", "Apple", "Banana", "Banana", "Mango", "Mango"])

    clf = ACBPClassifier(n_bins=3)
    clf.fit(X, y)

    result = clf.evaluate(X, y)

    assert result["accuracy"] == 1.0
    assert clf.relation_.declared_valid_count() == 6
    assert clf.relation_.truth_space_size() >= 6

    preds = clf.predict(pd.DataFrame({
        "Color": ["Red", "Yellow"],
        "Shape": ["Round", "Oval"],
    }))

    assert preds == ["Apple", "Mango"]


def test_acbp_classifier_ambiguous_color_only_is_not_forced_to_perfect():
    X = pd.DataFrame({
        "Color": ["Red", "Green", "Yellow", "Green", "Red", "Yellow"],
    })

    y = pd.Series(["Apple", "Apple", "Banana", "Banana", "Mango", "Mango"])

    clf = ACBPClassifier(n_bins=3)
    clf.fit(X, y)

    result = clf.evaluate(X, y)

    assert result["accuracy"] < 1.0
    assert clf.relation_.declared_valid_count() == 6

    explanation = clf.explain(pd.DataFrame({"Color": ["Red"]}), row_index=0)

    assert "ranked_candidates" in explanation
    assert explanation["truth_space_size"] == 12

    color_dimension_values = clf.binner_.dimension_values("Color")
    assert "Other" in color_dimension_values


def test_smooth_policy_predict_frame():
    X = pd.DataFrame({
        "Feature1": [1, 2, 3, 8, 9, 10],
        "Feature2": [1, 1, 2, 8, 9, 9],
    })

    y = pd.Series(["low", "low", "low", "high", "high", "high"])

    clf = ACBPClassifier(
        n_bins=3,
        policy=ACBPSmoothRiskPolicy(
            risk_class="high",
            risk_bias=0.05,
            support_bonus=0.05,
            exact_bonus=0.25,
        ),
    )

    clf.fit(X, y)

    pred_frame = clf.predict_frame(X, y)

    assert len(pred_frame) == len(X)
    assert "predicted" in pred_frame.columns
    assert "candidate_scores" in pred_frame.columns

    explanation = clf.explain(X, row_index=0)

    assert "ranked_candidates" in explanation
    assert "truth_space_size" in explanation


