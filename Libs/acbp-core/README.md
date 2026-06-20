# ACBP Core

ACBP Core is the foundational Python library for the Al-Anazi Categorical-Boolean Paradigm.

ACBP represents declared truth as categorical tuples and Boolean masks.

Core concepts:

- categorical dimensions
- declared valid truth tuples
- derived invalid tuples under closed-world declaration
- truth-space construction
- contradiction detection
- nearest valid repair
- policy-aware repair
- Boolean vector representation

This package is the reusable core engine used by ACBP Workbench and ACBP experiments.

## Install locally

From the main ACBP virtual environment:

python -m pip install -e D:\ACBP\Libs\acbp-core

## Example

from acbp import Dimension, MultiACBPRelation

dims = [
    Dimension("Object", ["Apple", "Banana", "Mango"]),
    Dimension("Color", ["Red", "Yellow", "Green"])
]

valid = {
    ("Apple", "Red"),
    ("Apple", "Green"),
    ("Banana", "Yellow"),
    ("Banana", "Green"),
    ("Mango", "Red"),
    ("Mango", "Yellow")
}

relation = MultiACBPRelation(dims, valid)
print(relation.valid_table())
print(relation.invalid_table())
