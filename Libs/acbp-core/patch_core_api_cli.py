from pathlib import Path

core = Path(r"D:\ACBP\Libs\acbp-core\src\acbp\multi.py")
text = core.read_text(encoding="utf-8")

compat = r'''

# ---------------------------------------------------------------------
# Convenience count methods
# ---------------------------------------------------------------------
def _acbp_multi_truth_space_size(self) -> int:
    size = 1
    for dim in self.dimensions:
        size *= len(dim.values)
    return size


def _acbp_multi_declared_valid_count(self) -> int:
    return len(self.valid_tuples)


def _acbp_multi_derived_invalid_count(self) -> int:
    return self.truth_space_size() - self.declared_valid_count()


if not hasattr(MultiACBPRelation, "truth_space_size"):
    MultiACBPRelation.truth_space_size = _acbp_multi_truth_space_size

if not hasattr(MultiACBPRelation, "declared_valid_count"):
    MultiACBPRelation.declared_valid_count = _acbp_multi_declared_valid_count

if not hasattr(MultiACBPRelation, "derived_invalid_count"):
    MultiACBPRelation.derived_invalid_count = _acbp_multi_derived_invalid_count
'''

if "_acbp_multi_truth_space_size" not in text:
    core.write_text(text.rstrip() + "\n\n" + compat.lstrip(), encoding="utf-8")
    print("Patched multi.py with count methods.")
else:
    print("multi.py already has count methods.")

cli = Path(r"D:\ACBP\Libs\acbp-core\src\acbp\cli.py")

cli_text = r'''from __future__ import annotations

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
'''

cli.write_text(cli_text, encoding="utf-8")
print("Patched cli.py.")
