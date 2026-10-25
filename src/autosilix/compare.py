"""PPA run comparison engine with compatibility checks and delta analysis."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from autosilix.exceptions import IncompatibleComparisonError
from autosilix.manifest import Manifest


class RunComparator:
    """Compares two implementation runs, checking validity and calculating deltas."""

    @classmethod
    def compare_runs(
        cls,
        manifest_a_path: str | Path,
        manifest_b_path: str | Path,
        strict_design_check: bool = True,
    ) -> dict[str, Any]:
        man_a = Manifest.load(manifest_a_path)
        man_b = Manifest.load(manifest_b_path)

        design_a = man_a.get("design_name")
        design_b = man_b.get("design_name")

        if strict_design_check and design_a != design_b:
            raise IncompatibleComparisonError(
                f"Incompatible run comparison: Design '{design_a}' vs '{design_b}'",
                details="Runs must target the same design for valid PPA trade-off comparison.",
            )

        metrics_a = man_a.get("metrics", {})
        metrics_b = man_b.get("metrics", {})

        all_keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))
        comparisons = []

        for key in all_keys:
            val_a = metrics_a.get(key, {}).get("value")
            val_b = metrics_b.get(key, {}).get("value")
            unit = metrics_a.get(key, {}).get("unit") or metrics_b.get(key, {}).get("unit")

            delta = None
            pct_change = None

            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                delta = round(val_b - val_a, 4)
                if val_a != 0:
                    pct_change = round(((val_b - val_a) / abs(val_a)) * 100.0, 2)

            comparisons.append({
                "metric": key,
                "val_a": val_a,
                "val_b": val_b,
                "unit": unit or "-",
                "delta": delta,
                "pct_change": pct_change,
            })

        return {
            "run_a": {
                "run_id": man_a.get("run_id"),
                "design": design_a,
                "status": man_a.get("status"),
                "duration": man_a.get("duration_seconds"),
            },
            "run_b": {
                "run_id": man_b.get("run_id"),
                "design": design_b,
                "status": man_b.get("status"),
                "duration": man_b.get("duration_seconds"),
            },
            "metrics": comparisons,
        }

    @classmethod
    def generate_markdown(cls, comp_data: dict[str, Any]) -> str:
        ra = comp_data["run_a"]
        rb = comp_data["run_b"]

        lines = [
            "# AutoSilix PPA Run Comparison",
            "",
            "| Attribute | Baseline Run (A) | Comparison Run (B) |",
            "|---|---|---|",
            f"| **Run ID** | `{ra['run_id']}` | `{rb['run_id']}` |",
            f"| **Design** | `{ra['design']}` | `{rb['design']}` |",
            f"| **Status** | `{ra['status']}` | `{rb['status']}` |",
            f"| **Duration** | {ra['duration']}s | {rb['duration']}s |",
            "",
            "## PPA Metric Differences",
            "",
            "| Metric | Run A | Run B | Unit | Delta (B - A) | % Change |",
            "|---|---|---|---|---|---|",
        ]

        for m in comp_data["metrics"]:
            name = m["metric"]
            va = m["val_a"] if m["val_a"] is not None else "N/A"
            vb = m["val_b"] if m["val_b"] is not None else "N/A"
            unit = m["unit"]
            delta = f"{m['delta']:+}" if m["delta"] is not None else "N/A"
            pct = f"{m['pct_change']:+.2f}%" if m["pct_change"] is not None else "N/A"
            lines.append(f"| `{name}` | {va} | {vb} | {unit} | {delta} | {pct} |")

        lines.extend([
            "",
            "> [!NOTE]",
            "> Percentage changes are calculated relative to Baseline Run (A).",
            "> Negative delta indicates reduction (e.g. smaller area or lower delay).",
        ])

        return "\n".join(lines) + "\n"

    @classmethod
    def generate_csv(cls, comp_data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["metric", "run_a_value", "run_b_value", "unit", "delta", "pct_change"])

        for m in comp_data["metrics"]:
            writer.writerow([
                m["metric"],
                m["val_a"],
                m["val_b"],
                m["unit"],
                m["delta"],
                m["pct_change"],
            ])

        return output.getvalue()
