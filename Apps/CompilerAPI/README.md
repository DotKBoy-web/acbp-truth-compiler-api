# ACBP Truth Compiler API

ACBP Truth Compiler API is a plugin-ready API for compiling categories, flags, dashboard states, workflow logic, and declared truths into auditable truth-space artifacts.

## What it does

Send structured categories, states, rules, dashboard outputs, or feature metadata.

Get back:

- truth-space size
- declared valid count
- derived invalid count
- truth density
- compact feature recommendations
- dashboard equivalence checks
- deterministic compiler brief
- exportable artifact packs

## Core endpoints

POST /v1/truth-space/compile
Purpose: Compile declared truth specs.

POST /v1/features/compact
Purpose: Recommend compact feature sets.

POST /v1/dashboard/compare
Purpose: Compare Live SQL vs compiled-state dashboard outputs.

GET /v1/clinical-dashboard/spec
Purpose: Return clinical dashboard compiler spec.

GET /v1/pricing
Purpose: Show plan limits.

GET /v1/examples
Purpose: Show example payloads.

## Authentication

Header name:

X-ACBP-API-Key

Example value:

acbp_free_demo

Local demo keys are stored in:

Apps/CompilerAPI/api_keys.json

## Guardrails

Truth space is not the confusion matrix.

Declared valid count is not prediction correctness.

Derived invalid count is not model error.

This API is for declared-truth modeling, dashboard logic validation, categorical-state reasoning, and operational state validation.
