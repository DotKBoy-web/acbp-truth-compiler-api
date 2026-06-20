from __future__ import annotations

import json
from itertools import product
from math import prod
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from acbp import Dimension, MultiACBPRelation
except Exception:
    from acbp.engine import Dimension
    from acbp.multi import MultiACBPRelation

from acbp_ml import ACBPBinner, auto_compact_features

from .models import ACBPCompileArtifact, ACBPCompilerOptions


def _make_dimension(name: str, values: list[str]):
    values = [str(v) for v in values]

    try:
        return Dimension(name=name, values=values)
    except TypeError:
        return Dimension(name, values)


def _make_relation(dimensions: list[Any], valid_tuples: set[tuple[str, ...]]):
    try:
        return MultiACBPRelation(dimensions=dimensions, valid_tuples=valid_tuples)
    except TypeError:
        try:
            return MultiACBPRelation(dimensions, valid_tuples)
        except TypeError:
            relation = MultiACBPRelation(dimensions)

            for item in valid_tuples:
                if hasattr(relation, "declare_valid"):
                    relation.declare_valid(item)

            if hasattr(relation, "valid_tuples"):
                relation.valid_tuples = valid_tuples

            return relation


def load_spec(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")

    if path.suffix.lower() == ".json":
        return json.loads(text)

    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except Exception as exc:
            raise RuntimeError("YAML specs require PyYAML. Use JSON or install PyYAML.") from exc

        return yaml.safe_load(text)

    raise ValueError(f"Unsupported spec file type: {path.suffix}")


def truth_space_size_from_dimensions(dimensions: list[Any]) -> int:
    counts = [len(getattr(d, "values")) for d in dimensions]
    return int(prod(counts)) if counts else 0


def relation_truth_space_size(relation: Any, dimensions: list[Any]) -> int:
    if hasattr(relation, "truth_space_size"):
        return int(relation.truth_space_size())

    return truth_space_size_from_dimensions(dimensions)


def compile_truth_spec(spec: dict[str, Any]) -> ACBPCompileArtifact:
    name = str(spec.get("name", "ACBP compiled truth spec"))
    target_col = str(spec.get("target_col", spec.get("target", {}).get("column", "TargetClass")))
    risk_class = spec.get("risk_class", spec.get("target", {}).get("risk_class"))

    dimension_specs = spec.get("dimensions", [])
    declared_truths = spec.get("declared_truths", [])

    if not dimension_specs:
        raise ValueError("Spec must include dimensions.")

    dimensions = []
    dimension_names = []

    for dim in dimension_specs:
        dim_name = str(dim["name"])
        values = [str(v) for v in dim["values"]]

        dimensions.append(_make_dimension(dim_name, values))
        dimension_names.append(dim_name)

    valid_tuples: set[tuple[str, ...]] = set()
    warnings: list[str] = []

    allowed = {
        dim["name"]: {str(v) for v in dim["values"]}
        for dim in dimension_specs
    }

    for row in declared_truths:
        if isinstance(row, dict):
            tup = tuple(str(row[name]) for name in dimension_names)
        else:
            tup = tuple(str(x) for x in row)

        if len(tup) != len(dimension_names):
            warnings.append(f"Skipped declared truth with wrong length: {tup}")
            continue

        invalid_parts = [
            f"{dimension_names[i]}={value}"
            for i, value in enumerate(tup)
            if value not in allowed[dimension_names[i]]
        ]

        if invalid_parts:
            warnings.append(f"Skipped declared truth outside dimension values: {', '.join(invalid_parts)}")
            continue

        valid_tuples.add(tup)

    relation = _make_relation(dimensions, valid_tuples)

    truth_space_size = relation_truth_space_size(relation, dimensions)
    declared_valid_count = len(valid_tuples)
    derived_invalid_count = max(truth_space_size - declared_valid_count, 0)
    density = declared_valid_count / truth_space_size if truth_space_size else 0.0

    features = [name for name in dimension_names if name != "TargetClass"]

    return ACBPCompileArtifact(
        name=name,
        target_col=target_col,
        risk_class=str(risk_class) if risk_class is not None else None,
        features=features,
        truth_space_size=truth_space_size,
        declared_valid_count=declared_valid_count,
        derived_invalid_count=derived_invalid_count,
        truth_density=density,
        warnings=warnings,
        relation=relation,
    )


def compile_dataframe(
    df: pd.DataFrame,
    target_col: str,
    features: list[str] | None = None,
    risk_class: str | None = None,
    name: str = "ACBP compiled dataset",
    options: ACBPCompilerOptions | None = None,
) -> ACBPCompileArtifact:
    options = options or ACBPCompilerOptions()

    if target_col not in df.columns:
        raise ValueError(f"Target column not found: {target_col}")

    clean = df.dropna(subset=[target_col]).copy()
    clean[target_col] = clean[target_col].astype(str)

    warnings: list[str] = []
    selected_details: list[dict[str, Any]] = []
    rejected_details: list[dict[str, Any]] = []
    excluded_details: list[dict[str, Any]] = []

    if options.auto_compact:
        compact = auto_compact_features(
            df=clean,
            target_col=target_col,
            candidate_features=features,
            n_bins=options.n_bins,
            max_features=options.max_features,
            max_truth_space=options.max_truth_space,
            min_density=options.min_density,
        )

        features = compact["selected_features"]
        selected_details = compact.get("selected_details", [])
        rejected_details = compact.get("rejected_details", [])
        excluded_details = compact.get("excluded_details", [])

        if not features:
            warnings.append("Auto Compact did not select any features.")

    if not features:
        features = [c for c in clean.columns if c != target_col]

    features = [f for f in features if f in clean.columns and f != target_col]

    if not features:
        raise ValueError("No usable features selected.")

    binner = ACBPBinner(n_bins=options.n_bins)
    Xb = binner.fit_transform(clean[features])

    target_values = sorted(clean[target_col].astype(str).unique().tolist())
    target_dimension = _make_dimension(options.target_dimension_name, target_values)

    feature_dimensions = [
        _make_dimension(feature, binner.dimension_values(feature))
        for feature in features
    ]

    dimensions = [target_dimension] + feature_dimensions

    compiled = pd.concat(
        [
            clean[[target_col]].rename(columns={target_col: options.target_dimension_name}).reset_index(drop=True),
            Xb.reset_index(drop=True),
        ],
        axis=1,
    )

    valid_tuples: set[tuple[str, ...]] = set()

    ordered_cols = [options.target_dimension_name] + features

    for _, row in compiled[ordered_cols].iterrows():
        valid_tuples.add(tuple(str(row[col]) for col in ordered_cols))

    relation = _make_relation(dimensions, valid_tuples)

    truth_space_size = relation_truth_space_size(relation, dimensions)
    declared_valid_count = len(valid_tuples)
    derived_invalid_count = max(truth_space_size - declared_valid_count, 0)
    density = declared_valid_count / truth_space_size if truth_space_size else 0.0

    if truth_space_size >= 1_000_000:
        warnings.append(
            "Large truth space detected. Prefer Auto Compact, fewer dimensions, or lower-cardinality categories."
        )

    if density < 0.01:
        warnings.append(
            "Very sparse declared-truth density detected. Predictions may rely heavily on nearest-truth repair."
        )

    return ACBPCompileArtifact(
        name=name,
        target_col=target_col,
        risk_class=risk_class,
        features=features,
        truth_space_size=truth_space_size,
        declared_valid_count=declared_valid_count,
        derived_invalid_count=derived_invalid_count,
        truth_density=density,
        warnings=warnings,
        selected_details=selected_details,
        rejected_details=rejected_details,
        excluded_details=excluded_details,
        relation=relation,
        binner=binner,
        compiled_frame=compiled,
    )


def compile_file(
    path: str | Path,
    target_col: str,
    features: list[str] | None = None,
    risk_class: str | None = None,
    name: str | None = None,
    options: ACBPCompilerOptions | None = None,
) -> ACBPCompileArtifact:
    path = Path(path)

    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported dataset file type: {path.suffix}")

    return compile_dataframe(
        df=df,
        target_col=target_col,
        features=features,
        risk_class=risk_class,
        name=name or path.stem,
        options=options,
    )


def enumerate_invalid_sample(
    artifact: ACBPCompileArtifact,
    limit: int = 100,
    max_scan: int = 250_000,
) -> list[dict[str, str]]:
    relation = artifact.relation

    if relation is None:
        return []

    dimensions = relation.dimensions
    names = [d.name for d in dimensions]
    valid = set(relation.valid_tuples)

    rows = []
    scanned = 0

    for tup in product(*[d.values for d in dimensions]):
        scanned += 1

        if tup not in valid:
            row = {names[i]: str(tup[i]) for i in range(len(names))}
            row["truth"] = "0"
            row["state"] = "INVALID"
            rows.append(row)

            if len(rows) >= limit:
                break

        if scanned >= max_scan:
            break

    return rows
