"""PPA metrics extraction, provenance tracking, and report parsing engine."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class MetricRecord:
    """A single implementation metric with full provenance and source attribution."""

    name: str
    value: float | int | str | None
    unit: str | None
    stage: str
    source_file: str
    parser_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MetricsExtractor:
    """Extracts PPA metrics from raw EDA tool logs and reports."""

    PARSER_VERSION = "1.0.0"

    @classmethod
    def extract_all(cls, run_dir: Path) -> dict[str, dict[str, Any]]:
        """Extract all discoverable metrics from reports and logs in run_dir."""
        metrics: dict[str, MetricRecord] = {}

        # 1. Synthesis report
        synth_rpt = run_dir / "reports" / "synthesis.rpt"
        if synth_rpt.is_file():
            cls._parse_synthesis_report(synth_rpt, metrics)

        # 2. Floorplan report
        fp_rpt = run_dir / "reports" / "floorplan.rpt"
        if fp_rpt.is_file():
            cls._parse_floorplan_report(fp_rpt, metrics)

        # 3. Routing report
        route_rpt = run_dir / "reports" / "routing.rpt"
        if route_rpt.is_file():
            cls._parse_routing_report(route_rpt, metrics)

        # 4. STA report
        sta_rpt = run_dir / "reports" / "sta.rpt"
        if sta_rpt.is_file():
            cls._parse_sta_report(sta_rpt, metrics)

        # 5. CTS report
        cts_rpt = run_dir / "reports" / "cts.rpt"
        if cts_rpt.is_file():
            cls._parse_cts_report(cts_rpt, metrics)

        # 6. DRC report
        drc_rpt = run_dir / "reports" / "drc.rpt"
        if drc_rpt.is_file():
            cls._parse_drc_report(drc_rpt, metrics)

        return {name: m.to_dict() for name, m in metrics.items()}

    @classmethod
    def _parse_synthesis_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        # Cell area: Chip area for module '...': 124.50 um^2
        m_area = re.search(r"Chip area for module [^:]+:\s*([0-9.]+)\s*(um\^2)?", text)
        if m_area:
            out["cell_area"] = MetricRecord(
                name="cell_area",
                value=float(m_area.group(1)),
                unit="um^2",
                stage="synthesis",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # Number of cells
        m_cells = re.search(r"Number of cells:\s*(\d+)", text)
        if m_cells:
            out["cell_count"] = MetricRecord(
                name="cell_count",
                value=int(m_cells.group(1)),
                unit=None,
                stage="synthesis",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # Number of sequential cells / DFFs
        m_dff = re.search(r"\$_DFF_\S+\s*(\d+)", text)
        if m_dff:
            out["sequential_cell_count"] = MetricRecord(
                name="sequential_cell_count",
                value=int(m_dff.group(1)),
                unit=None,
                stage="synthesis",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

    @classmethod
    def _parse_floorplan_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        m_die = re.search(r"Die area:\s*[0-9.]+\s+[0-9.]+\s+([0-9.]+)\s+([0-9.]+)\s*\(([0-9.]+)\s*um\^2\)", text)
        if m_die:
            out["die_area"] = MetricRecord(
                name="die_area",
                value=float(m_die.group(3)),
                unit="um^2",
                stage="floorplan",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        m_core = re.search(r"Core area:\s*[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s*\(([0-9.]+)\s*um\^2\)", text)
        if m_core:
            out["core_area"] = MetricRecord(
                name="core_area",
                value=float(m_core.group(1)),
                unit="um^2",
                stage="floorplan",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        m_util = re.search(r"Core utilization:\s*([0-9.]+)\s*%", text)
        if m_util:
            out["core_utilization"] = MetricRecord(
                name="core_utilization",
                value=float(m_util.group(1)),
                unit="%",
                stage="floorplan",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

    @classmethod
    def _parse_routing_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        m_wire = re.search(r"Total wire length:\s*([0-9.]+)\s*(um)?", text)
        if m_wire:
            out["wire_length"] = MetricRecord(
                name="wire_length",
                value=float(m_wire.group(1)),
                unit="um",
                stage="routing",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        m_unrouted = re.search(r"Unrouted nets:\s*(\d+)", text)
        if m_unrouted:
            out["unrouted_nets"] = MetricRecord(
                name="unrouted_nets",
                value=int(m_unrouted.group(1)),
                unit=None,
                stage="routing",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        m_drc = re.search(r"DRC violations:\s*(\d+)", text)
        if m_drc:
            out["route_drc_violations"] = MetricRecord(
                name="route_drc_violations",
                value=int(m_drc.group(1)),
                unit=None,
                stage="routing",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

    @classmethod
    def _parse_sta_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        # Clock target
        m_clk = re.search(r"Clock target:\s*([0-9.]+)\s*ns", text)
        if m_clk:
            out["clock_target"] = MetricRecord(
                name="clock_target",
                value=float(m_clk.group(1)),
                unit="ns",
                stage="sta",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # WNS
        m_wns = re.search(r"Worst Negative Slack \(WNS\):\s*(-?[0-9.]+)\s*ns", text)
        if m_wns:
            out["worst_negative_slack"] = MetricRecord(
                name="worst_negative_slack",
                value=float(m_wns.group(1)),
                unit="ns",
                stage="sta",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # TNS
        m_tns = re.search(r"Total Negative Slack \(TNS\):\s*(-?[0-9.]+)\s*ns", text)
        if m_tns:
            out["total_negative_slack"] = MetricRecord(
                name="total_negative_slack",
                value=float(m_tns.group(1)),
                unit="ns",
                stage="sta",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # Critical path delay
        m_crit = re.search(r"Critical path delay:\s*([0-9.]+)\s*ns", text)
        if m_crit:
            out["critical_path_delay"] = MetricRecord(
                name="critical_path_delay",
                value=float(m_crit.group(1)),
                unit="ns",
                stage="sta",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        # Slack
        m_slack = re.search(r"Slack:\s*(-?[0-9.]+)\s*ns", text)
        if m_slack:
            out["setup_slack"] = MetricRecord(
                name="setup_slack",
                value=float(m_slack.group(1)),
                unit="ns",
                stage="sta",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

    @classmethod
    def _parse_cts_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        m_buf = re.search(r"Number of clock buffers inserted:\s*(\d+)", text)
        if m_buf:
            out["clock_buffer_count"] = MetricRecord(
                name="clock_buffer_count",
                value=int(m_buf.group(1)),
                unit=None,
                stage="cts",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

        m_skew = re.search(r"Clock skew:\s*([0-9.]+)\s*ns", text)
        if m_skew:
            out["clock_skew"] = MetricRecord(
                name="clock_skew",
                value=float(m_skew.group(1)),
                unit="ns",
                stage="cts",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )

    @classmethod
    def _parse_drc_report(cls, path: Path, out: dict[str, MetricRecord]) -> None:
        rel_path = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return

        m_viol = re.search(r"Violations found:\s*(\d+)", text)
        if m_viol:
            out["physical_drc_violations"] = MetricRecord(
                name="physical_drc_violations",
                value=int(m_viol.group(1)),
                unit=None,
                stage="drc",
                source_file=rel_path,
                parser_version=cls.PARSER_VERSION,
            )
