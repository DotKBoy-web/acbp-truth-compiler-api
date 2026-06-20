from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ACBPCompilerOptions:
    n_bins: int = 3
    auto_compact: bool = False
    max_features: int = 6
    max_truth_space: int = 20_000
    min_density: float = 0.02
    target_dimension_name: str = "TargetClass"


@dataclass
class ACBPCompileArtifact:
    name: str
    target_col: str
    risk_class: str | None
    features: list[str]
    truth_space_size: int
    declared_valid_count: int
    derived_invalid_count: int
    truth_density: float
    warnings: list[str] = field(default_factory=list)
    selected_details: list[dict[str, Any]] = field(default_factory=list)
    rejected_details: list[dict[str, Any]] = field(default_factory=list)
    excluded_details: list[dict[str, Any]] = field(default_factory=list)
    relation: Any = None
    binner: Any = None
    compiled_frame: Any = None

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target_col": self.target_col,
            "risk_class": self.risk_class,
            "features": self.features,
            "truth_space_size": self.truth_space_size,
            "declared_valid_count": self.declared_valid_count,
            "derived_invalid_count": self.derived_invalid_count,
            "truth_density": self.truth_density,
            "warnings": self.warnings,
            "selected_details": self.selected_details,
            "rejected_details": self.rejected_details,
            "excluded_details": self.excluded_details,
        }

    def deterministic_brief(self) -> str:
        feature_text = ", ".join(self.features)

        warnings = ""
        if self.warnings:
            warnings = "\nWarnings:\n" + "\n".join(f"- {w}" for w in self.warnings)

        return f"""ACBP Compiler deterministic brief

Model name: {self.name}
Target/state column: {self.target_col}
Selected dimensions: {feature_text}
Risk class: {self.risk_class}

Truth-space meaning:
Truth space = TargetClass x selected categorical/binned feature dimensions.
Declared valid truths = observed or declared class-feature tuples.
Derived invalid truths = unobserved class-feature tuples under closed-world declaration.
Truth space is not the confusion matrix.

Truth-space size: {self.truth_space_size}
Declared valid count: {self.declared_valid_count}
Derived invalid count: {self.derived_invalid_count}
Truth density: {self.truth_density:.6f}

Guardrails:
Declared valid count is not correct predictions.
Derived invalid count is not prediction errors.
Compiler output is a declared-truth model, not a clinical deployment.
{warnings}
"""

