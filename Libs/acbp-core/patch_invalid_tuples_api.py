from pathlib import Path

p = Path(r"D:\ACBP\Libs\acbp-core\src\acbp\multi.py")
text = p.read_text(encoding="utf-8")

compat = r'''

# ---------------------------------------------------------------------
# Complement invalid tuple API
# ---------------------------------------------------------------------
def _acbp_multi_invalid_tuples(self) -> set[tuple]:
    from itertools import product

    dimension_values = [tuple(dim.values) for dim in self.dimensions]
    all_tuples = set(product(*dimension_values))
    return all_tuples - set(self.valid_tuples)


if not hasattr(MultiACBPRelation, "invalid_tuples"):
    MultiACBPRelation.invalid_tuples = _acbp_multi_invalid_tuples
'''

if "_acbp_multi_invalid_tuples" not in text:
    p.write_text(text.rstrip() + "\n\n" + compat.lstrip(), encoding="utf-8")
    print("Patched invalid_tuples into MultiACBPRelation.")
else:
    print("invalid_tuples patch already exists.")
