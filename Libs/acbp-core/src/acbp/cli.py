from __future__ import annotations

import argparse

from acbp import Dimension, MultiACBPRelation


def demo_object_color() -> None:
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

    relation = MultiACBPRelation(
        dimensions=dims,
        valid_tuples=valid,
        name="ACBP Object-Color Demo",
    )

    print("ACBP Core Demo")
    print("==============")
    print(f"Relation: {relation.name}")
    print(f"Dimensions: {len(relation.dimensions)}")
    print(f"Truth space size: {relation.truth_space_size()}")
    print(f"Declared valid truths: {relation.declared_valid_count()}")
    print(f"Derived invalid truths: {relation.derived_invalid_count()}")
    print()
    print("Declared valid table:")
    print(relation.valid_table().to_string(index=False))
    print()
    print("Derived invalid table:")
    print(relation.invalid_table().to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="acbp",
        description="ACBP Core CLI",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("demo", help="Run the built-in ACBP object-color demo")

    args = parser.parse_args()

    if args.command == "demo":
        demo_object_color()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
