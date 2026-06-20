from acbp import Dimension, MultiACBPRelation


def make_object_color_relation():
    dims = [
        Dimension("Object", ["Apple", "Banana", "Mango"]),
        Dimension("Color", ["Red", "Yellow", "Green"]),
    ]

    valid = {
        ("Apple", "Red"),
        ("Apple", "Green"),
        ("Banana", "Yellow"),
        ("Banana", "Green"),
        ("Mango", "Red"),
        ("Mango", "Yellow"),
    }

    return MultiACBPRelation(
        dimensions=dims,
        valid_tuples=valid,
        name="Object-Color Test Relation",
    )


def test_truth_space_counts():
    relation = make_object_color_relation()

    assert relation.truth_space_size() == 9
    assert relation.declared_valid_count() == 6
    assert relation.derived_invalid_count() == 3


def test_invalid_tuples_are_complement():
    relation = make_object_color_relation()

    invalid = relation.invalid_tuples()

    assert ("Apple", "Yellow") in invalid
    assert ("Banana", "Red") in invalid
    assert ("Mango", "Green") in invalid

    assert ("Apple", "Red") not in invalid
    assert ("Banana", "Yellow") not in invalid
    assert ("Mango", "Yellow") not in invalid


def test_valid_table_shape():
    relation = make_object_color_relation()

    table = relation.valid_table()

    assert len(table) == 6
    assert "Object" in table.columns
    assert "Color" in table.columns
    assert "truth" in table.columns
    assert "state" in table.columns
    assert "vector" in table.columns


def test_invalid_table_shape():
    relation = make_object_color_relation()

    table = relation.invalid_table()

    assert len(table) == 3
    assert set(table["state"]) == {"INVALID"}
    assert set(table["truth"]) == {0}


def test_boolean_vectors():
    relation = make_object_color_relation()

    invalid = relation.invalid_table()
    vectors = set(invalid["vector"].astype(str))

    assert "100010" in vectors
    assert "010100" in vectors
    assert "001001" in vectors
