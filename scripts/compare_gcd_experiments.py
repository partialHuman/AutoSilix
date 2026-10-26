import json
import os

base_path = "experiments/gcd/baseline/6_report_original.json"
exp1_path = "eda/OpenROAD-flow-scripts/flow/logs/sky130hd/gcd/exp01/6_report.json"
exp2_path = "eda/OpenROAD-flow-scripts/flow/logs/sky130hd/gcd/exp02/6_report.json"
exp3_path = "eda/OpenROAD-flow-scripts/flow/logs/sky130hd/gcd/exp03/6_report.json"
exp4_path = "eda/OpenROAD-flow-scripts/flow/logs/sky130hd/gcd/exp04/6_report.json"

base = json.load(open(base_path, encoding="utf-8"))
exp1 = json.load(open(exp1_path, encoding="utf-8"))
exp2 = json.load(open(exp2_path, encoding="utf-8"))
exp3 = json.load(open(exp3_path, encoding="utf-8"))
exp4 = json.load(open(exp4_path, encoding="utf-8")) if os.path.exists(exp4_path) else None

metrics = [
    ("Setup WNS (ns)", "finish__timing__setup__ws", 1.0, "{:.4f}"),
    ("Setup TNS (ns)", "finish__timing__setup__tns", 1.0, "{:.4f}"),
    ("Hold WNS (ns)", "finish__timing__hold__ws", 1.0, "{:.4f}"),
    ("Hold TNS (ns)", "finish__timing__hold__tns", 1.0, "{:.4f}"),
    ("Fmax (MHz)", "finish__timing__fmax", 1e-6, "{:.2f}"),
    ("Setup Violations", "finish__timing__drv__setup_violation_count", 1, "{:d}"),
    ("Hold Violations", "finish__timing__drv__hold_violation_count", 1, "{:d}"),
    ("Std-Cell Area (um^2)", "finish__design__instance__area__stdcell", 1.0, "{:.2f}"),
    ("Core Utilization (%)", "finish__design__instance__utilization__stdcell", 100.0, "{:.2f}"),
    ("Total Instances", "finish__design__instance__count", 1, "{:d}"),
    ("Std-Cell Count", "finish__design__instance__count__stdcell", 1, "{:d}"),
    ("Timing Repair Buffers", "finish__design__instance__count__class:timing_repair_buffer", 1, "{:d}"),
    ("Timing Repair Area (um^2)", "finish__design__instance__area__class:timing_repair_buffer", 1.0, "{:.2f}"),
    ("Total Power (mW)", "finish__power__total", 1000.0, "{:.3f}"),
    ("Internal Power (mW)", "finish__power__internal__total", 1000.0, "{:.3f}"),
    ("Switching Power (mW)", "finish__power__switching__total", 1000.0, "{:.3f}"),
    ("Leakage Power (uW)", "finish__power__leakage__total", 1e6, "{:.4f}"),
    ("Die Area (um^2)", "finish__design__die__area", 1.0, "{:.2f}"),
    ("Core Area (um^2)", "finish__design__core__area", 1.0, "{:.2f}")
]

if exp4:
    header = f"| {'Metric':<25} | {'Baseline':<10} | {'Exp 01':<10} | {'Exp 02':<10} | {'Exp 03':<10} | {'Exp 04':<10} | {'Exp04 vs Base':<17} | {'Exp04 vs Exp01':<17} | {'Exp04 vs Exp03':<17} |"
    sep = "|" + "-"*27 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*19 + "|" + "-"*19 + "|" + "-"*19 + "|"
    print(header)
    print(sep)
    for label, key, scale, fmt in metrics:
        vb = base.get(key, 0) * scale
        v1 = exp1.get(key, 0) * scale
        v2 = exp2.get(key, 0) * scale
        v3 = exp3.get(key, 0) * scale
        v4 = exp4.get(key, 0) * scale

        delta_b = v4 - vb
        pct_b = (delta_b / abs(vb) * 100.0) if vb != 0 else 0.0
        delta_1 = v4 - v1
        pct_1 = (delta_1 / abs(v1) * 100.0) if v1 != 0 else 0.0
        delta_3 = v4 - v3
        pct_3 = (delta_3 / abs(v3) * 100.0) if v3 != 0 else 0.0

        sb = fmt.format(vb)
        s1 = fmt.format(v1)
        s2 = fmt.format(v2)
        s3 = fmt.format(v3)
        s4 = fmt.format(v4)

        diff_b_str = f"{delta_b:+.4f} ({pct_b:+.1f}%)" if "{" in fmt and "d" not in fmt else f"{int(delta_b):+d} ({pct_b:+.1f}%)"
        diff_1_str = f"{delta_1:+.4f} ({pct_1:+.1f}%)" if "{" in fmt and "d" not in fmt else f"{int(delta_1):+d} ({pct_1:+.1f}%)"
        diff_3_str = f"{delta_3:+.4f} ({pct_3:+.1f}%)" if "{" in fmt and "d" not in fmt else f"{int(delta_3):+d} ({pct_3:+.1f}%)"

        print(f"| {label:<25} | {sb:<10} | {s1:<10} | {s2:<10} | {s3:<10} | {s4:<10} | {diff_b_str:<17} | {diff_1_str:<17} | {diff_3_str:<17} |")
else:
    header = f"| {'Metric':<25} | {'Baseline':<10} | {'Exp 01':<10} | {'Exp 02':<10} | {'Exp 03':<10} |"
    sep = "|" + "-"*27 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|"
    print(header)
    print(sep)
    for label, key, scale, fmt in metrics:
        vb = base.get(key, 0) * scale
        v1 = exp1.get(key, 0) * scale
        v2 = exp2.get(key, 0) * scale
        v3 = exp3.get(key, 0) * scale
        print(f"| {label:<25} | {fmt.format(vb):<10} | {fmt.format(v1):<10} | {fmt.format(v2):<10} | {fmt.format(v3):<10} |")
