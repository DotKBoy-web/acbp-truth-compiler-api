from pathlib import Path

p = Path(r"D:\ACBP\Libs\acbp-compiler\pyproject.toml")

text = """[project]
name = "acbp-compiler"
version = "0.1.0"
description = "ACBP compiler for declared-truth specifications and datasets"
requires-python = ">=3.10"
dependencies = [
    "pandas"
]

[project.scripts]
acbp-compile = "acbp_compiler.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/acbp_compiler"]

[tool.hatch.build.targets.editable]
packages = ["src/acbp_compiler"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

p.write_text(text, encoding="utf-8")

# Validate TOML immediately
import tomllib
tomllib.loads(p.read_text(encoding="utf-8"))
print("pyproject.toml fixed and valid.")
