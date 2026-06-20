from pathlib import Path
import tomllib

path = Path(r"D:\ACBP\Libs\acbp-core\pyproject.toml")

content = """[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "acbp-core"
version = "0.1.0"
description = "ACBP Core: Al-Anazi Categorical-Boolean Paradigm truth-space engine"
readme = "README.md"
requires-python = ">=3.10"
authors = [
    { name = "Mutaib Al-Anazi" }
]
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0"
]

[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
acbp = "acbp.cli:main"
"""

path.write_text(content, encoding="utf-8")

with path.open("rb") as f:
    parsed = tomllib.load(f)

print("pyproject.toml fixed and valid.")
print(parsed["project"]["name"], parsed["project"]["version"])
