from pathlib import Path

p = Path(r"D:\ACBP\Libs\acbp-ml\src\acbp_ml\binning.py")
text = p.read_text(encoding="utf-8-sig")

text = text.replace(
'class ACBPBinner:
    n_bins: int = 3
    max_categories: int = 30
    transformers_: dict = field(default_factory=dict)',
'class ACBPBinner:
    n_bins: int = 3
    max_categories: int = 30
    low_cardinality_numeric_as_category: int = 10
    transformers_: dict = field(default_factory=dict)'
)

old = '''            if pd.api.types.is_numeric_dtype(s):
                thresholds = [
                    float(s.quantile(i / self.n_bins))
                    for i in range(1, self.n_bins)
                ]

                self.transformers_[col] = {
                    "type": "numeric",
                    "labels": labels,
                    "thresholds": thresholds,
                    "values": labels,
                }
            else:
                values = (
                    s.astype(str)
                    .fillna("Missing")
                    .replace({"nan": "Missing", "None": "Missing", "": "Missing"})
                )

                cats = list(values.value_counts().head(self.max_categories).index)

                if "Other" not in cats:
                    cats.append("Other")

                self.transformers_[col] = {
                    "type": "categorical",
                    "categories": cats,
                    "values": cats,
                }'''

new = '''            if pd.api.types.is_numeric_dtype(s) and s.nunique(dropna=True) > self.low_cardinality_numeric_as_category:
                thresholds = [
                    float(s.quantile(i / self.n_bins))
                    for i in range(1, self.n_bins)
                ]

                self.transformers_[col] = {
                    "type": "numeric",
                    "labels": labels,
                    "thresholds": thresholds,
                    "values": labels,
                }
            else:
                values = (
                    s.astype(str)
                    .fillna("Missing")
                    .replace({"nan": "Missing", "None": "Missing", "": "Missing"})
                )

                cats = list(values.value_counts().head(self.max_categories).index)

                if "Other" not in cats:
                    cats.append("Other")

                self.transformers_[col] = {
                    "type": "categorical",
                    "categories": cats,
                    "values": cats,
                }'''

if old not in text:
    print("Expected binner block not found. It may already be patched.")
else:
    text = text.replace(old, new)

p.write_text(text, encoding="utf-8")
print("Patched ACBPBinner.")
