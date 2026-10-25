"""Command Line Interface (CLI) for AutoSilix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autosilix import __version__
from autosilix.compare import RunComparator
from autosilix.config import ConfigManager
from autosilix.exceptions import AutoSilixError, IncompatibleComparisonError
from autosilix.manifest import Manifest
from autosilix.report import ReportGenerator
from autosilix.toolchain import ToolchainDetector
from autosilix.workflow import WorkflowEngine


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autosilix",
        description="AutoSilix — Reproducible RTL-to-GDSII Automation and PPA Analysis Framework",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: validate
    val_p = subparsers.add_parser("validate", help="Validate a design/workflow configuration file")
    val_p.add_argument("--config", "-c", required=True, help="Path to YAML configuration file")

    # Command: run
    run_p = subparsers.add_parser("run", help="Execute an RTL-to-GDSII implementation flow")
    run_p.add_argument("--config", "-c", required=True, help="Path to YAML configuration file")
    run_p.add_argument("--mock", action="store_true", help="Run in mock mode for validation/testing")
    run_p.add_argument("--stages", help="Comma-separated list of specific stages to execute")
    run_p.add_argument("--fail-fast", dest="fail_fast", action="store_true", default=None, help="Abort flow on first stage failure")
    run_p.add_argument("--run-id", help="Explicit custom run ID (default: unique timestamped ID)")
    run_p.add_argument("--runs-dir", default="runs", help="Base directory for run artifacts (default: runs)")

    # Command: status
    stat_p = subparsers.add_parser("status", help="Query execution status of a previous run")
    stat_p.add_argument("--run-id", "-r", required=True, help="Run identifier to inspect")
    stat_p.add_argument("--runs-dir", default="runs", help="Base directory for runs")

    # Command: report
    rep_p = subparsers.add_parser("report", help="Display or generate summary report for a completed run")
    rep_p.add_argument("--run-id", "-r", required=True, help="Run identifier")
    rep_p.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown", help="Report format")
    rep_p.add_argument("--runs-dir", default="runs", help="Base directory for runs")

    # Command: compare
    comp_p = subparsers.add_parser("compare", help="Compare PPA metrics between two runs")
    comp_p.add_argument("--runs", nargs=2, required=True, metavar=("RUN_A", "RUN_B"), help="Two Run IDs or manifest paths")
    comp_p.add_argument("--format", choices=["markdown", "csv"], default="markdown", help="Comparison format")
    comp_p.add_argument("--runs-dir", default="runs", help="Base directory for runs")

    # Command: tools
    subparsers.add_parser("tools", help="Audit installed EDA tools and host environment")

    return parser


def locate_manifest(run_id_or_path: str, runs_dir: str = "runs") -> Path:
    """Find manifest.json given a run ID or direct file path."""
    p = Path(run_id_or_path)
    if p.is_file() and p.name == "manifest.json":
        return p
    if p.is_dir() and (p / "manifest.json").is_file():
        return p / "manifest.json"

    # Search inside runs_dir
    base = Path(runs_dir)
    matches = list(base.glob(f"**/{run_id_or_path}/manifest.json"))
    if matches:
        return matches[0]

    raise FileNotFoundError(f"Manifest for run '{run_id_or_path}' not found in {runs_dir}")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        cfg = ConfigManager.load(args.config)
        print(f"[OK] Configuration '{Path(args.config).name}' is valid.")
        print(f"     Design: {cfg.design.name} (Top: {cfg.design.top_module})")
        print(f"     PDK: {cfg.pdk.name} ({cfg.pdk.variant})")
        print(f"     Clock Period: {cfg.constraints.clock_period} {cfg.constraints.time_unit}")
        print(f"     Configured Stages: {', '.join(cfg.flow.stages)}")
        print(f"     Config SHA256: {cfg.config_hash[:16]}...")
        return 0
    except AutoSilixError as e:
        print(f"[ERROR] Validation failed:\n{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}", file=sys.stderr)
        return 2


def cmd_run(args: argparse.Namespace) -> int:
    try:
        cfg = ConfigManager.load(args.config)

        if args.fail_fast is not None:
            cfg.flow.fail_fast = args.fail_fast

        selected_stages = [s.strip() for s in args.stages.split(",")] if args.stages else None

        print("=== Starting AutoSilix Workflow ===")
        print(f"Design: {cfg.design.name} | Top: {cfg.design.top_module}")
        print(f"Mode: {'MOCK (Testing)' if args.mock else 'REAL EDA FLOW'}")

        engine = WorkflowEngine(
            config=cfg,
            run_id=args.run_id,
            base_runs_dir=args.runs_dir,
            mock=args.mock,
            selected_stages=selected_stages,
        )

        manifest = engine.run()
        manifest_data = manifest.to_dict()

        # Save Markdown, JSON, and CSV reports
        ReportGenerator.save_all_reports(manifest_data, engine.artifacts.run_dir)

        print("\n=== Stage Results ===")
        for s_name, s_res in manifest_data["stages"].items():
            state = s_res["state"]
            symbol = "[PASS]" if state == "PASS" else ("[FAIL]" if state == "FAIL" else "[SKIP]")
            print(f" {symbol:<6} {s_name:<16} : {state} ({s_res['duration_seconds']:.2f}s)")

        print("\n=== Workflow Summary ===")
        print(f"Run ID: {manifest.run_id}")
        print(f"Status: {manifest.status}")
        print(f"Duration: {manifest.duration_seconds:.2f}s")
        print(f"Artifacts: {engine.artifacts.run_dir}")

        return 0 if manifest.status == "PASS" else 1

    except AutoSilixError as e:
        print(f"[ERROR] Run failed:\n{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}", file=sys.stderr)
        return 2


def cmd_status(args: argparse.Namespace) -> int:
    try:
        manifest_path = locate_manifest(args.run_id, args.runs_dir)
        data = Manifest.load(manifest_path)

        print(f"=== AutoSilix Run Status: {data.get('run_id')} ===")
        print(f"Design   : {data.get('design_name')}")
        print(f"Status   : {data.get('status')}")
        print(f"Duration : {data.get('duration_seconds')}s")
        print(f"Started  : {data.get('start_time')}")
        print(f"Ended    : {data.get('end_time')}")

        print("\nStages:")
        for s_name, s_info in data.get("stages", {}).items():
            print(f"  - {s_name:<16} : {s_info.get('state')} ({s_info.get('duration_seconds')}s)")

        return 0
    except Exception as e:
        print(f"[ERROR] Failed to query status: {e}", file=sys.stderr)
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    try:
        manifest_path = locate_manifest(args.run_id, args.runs_dir)
        data = Manifest.load(manifest_path)

        if args.format == "markdown":
            print(ReportGenerator.generate_markdown(data))
        elif args.format == "json":
            print(ReportGenerator.generate_json_summary(data))
        elif args.format == "csv":
            print(ReportGenerator.generate_csv_metrics(data))

        return 0
    except Exception as e:
        print(f"[ERROR] Failed to generate report: {e}", file=sys.stderr)
        return 1


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        man_a_path = locate_manifest(args.runs[0], args.runs_dir)
        man_b_path = locate_manifest(args.runs[1], args.runs_dir)

        comp = RunComparator.compare_runs(man_a_path, man_b_path)

        if args.format == "markdown":
            print(RunComparator.generate_markdown(comp))
        elif args.format == "csv":
            print(RunComparator.generate_csv(comp))

        return 0
    except IncompatibleComparisonError as e:
        print(f"[INCOMPATIBLE COMPARISON] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Comparison failed: {e}", file=sys.stderr)
        return 1


def cmd_tools() -> int:
    print("=== AutoSilix EDA Toolchain Audit ===")
    inventory = ToolchainDetector.get_inventory()
    print(f"{'Tool':<12} {'Available':<12} {'Version':<20} {'Command / Path'}")
    print("-" * 75)
    for name, info in inventory.items():
        avail_str = "YES" if info.available else "NO"
        v_str = info.version or "-"
        path_str = info.path or info.command
        print(f"{name:<12} {avail_str:<12} {v_str:<20} {path_str}")

    env = ToolchainDetector.get_environment_info()
    print("\nHost Environment:")
    print(f"  OS         : {env['os']}")
    print(f"  Python     : {env['python_version']}")
    print(f"  Git Commit : {env.get('git_commit') or 'None'}")
    print(f"  Git Dirty  : {env.get('git_dirty')}")

    return 0


def main(argv: list[str] | None = None) -> int:
    # Ensure UTF-8 output handling on Windows consoles
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "validate":
        return cmd_validate(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "compare":
        return cmd_compare(args)
    elif args.command == "tools":
        return cmd_tools()

    return 0


if __name__ == "__main__":
    sys.exit(main())
