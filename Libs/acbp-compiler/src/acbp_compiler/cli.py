from __future__ import annotations

import argparse
import json

from .compiler import compile_file, compile_truth_spec, load_spec
from .dashboard_equivalence import compare_dashboard_result_files, latency_comparison
from .clinical_dashboard import compile_clinical_dashboard_spec, compare_live_sql_and_cbp_paths
from .models import ACBPCompilerOptions


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(prog="acbp-compile")
    sub = parser.add_subparsers(dest="command", required=True)

    spec_parser = sub.add_parser("spec", help="Compile an ACBP JSON/YAML truth spec.")
    spec_parser.add_argument("path")

    data_parser = sub.add_parser("data", help="Compile a CSV/XLSX dataset into an ACBP declared-truth model.")
    data_parser.add_argument("path")
    data_parser.add_argument("--target", required=True)
    data_parser.add_argument("--risk-class", default=None)
    data_parser.add_argument("--features", default="")
    data_parser.add_argument("--auto-compact", action="store_true")
    data_parser.add_argument("--max-features", type=int, default=6)
    data_parser.add_argument("--max-truth-space", type=int, default=20_000)
    data_parser.add_argument("--min-density", type=float, default=0.02)
    data_parser.add_argument("--bins", type=int, default=3)

    clinical_parser = sub.add_parser("clinical-dashboard", help="Compile the FAC_01 IPD clinical dashboard Live SQL vs CBP spec.")
    clinical_parser.add_argument("--compare-paths", action="store_true")

    compare_parser = sub.add_parser("dashboard-compare", help="Compare Live SQL and CBP dashboard result exports.")
    compare_parser.add_argument("--live", required=True)
    compare_parser.add_argument("--cbp", required=True)
    compare_parser.add_argument("--keys", default="")
    compare_parser.add_argument("--ignore", default="")
    compare_parser.add_argument("--tolerance", type=float, default=0.000001)
    compare_parser.add_argument("--live-ms", type=float, default=None)
    compare_parser.add_argument("--cbp-ms", type=float, default=None)

    args = parser.parse_args()

    if args.command == "spec":
        spec = load_spec(args.path)
        artifact = compile_truth_spec(spec)
        print(json.dumps(artifact.summary(), indent=2, ensure_ascii=False))
        return

    if args.command == "clinical-dashboard":
        if args.compare_paths:
            print(json.dumps(compare_live_sql_and_cbp_paths(), indent=2, ensure_ascii=False))
        else:
            artifact = compile_clinical_dashboard_spec()
            print(json.dumps(artifact.summary(), indent=2, ensure_ascii=False))
        return

    if args.command == "dashboard-compare":
        result = compare_dashboard_result_files(
            live_path=args.live,
            cbp_path=args.cbp,
            key_cols=_split_csv(args.keys),
            ignore_cols=_split_csv(args.ignore),
            tolerance=args.tolerance,
        )

        if args.live_ms is not None and args.cbp_ms is not None:
            result["latency"] = latency_comparison(args.live_ms, args.cbp_ms)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "data":
        features = _split_csv(args.features)

        options = ACBPCompilerOptions(
            n_bins=args.bins,
            auto_compact=args.auto_compact,
            max_features=args.max_features,
            max_truth_space=args.max_truth_space,
            min_density=args.min_density,
        )

        artifact = compile_file(
            path=args.path,
            target_col=args.target,
            features=features or None,
            risk_class=args.risk_class,
            options=options,
        )

        print(json.dumps(artifact.summary(), indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
