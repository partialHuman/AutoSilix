# PPA Comparison: GCD Baseline vs. Exp 01 vs. Exp 02 vs. Exp 03 vs. Exp 04

## 1. Executive Summary

Experiment 04 evaluated the **Composite Hypothesis: Unified Comparator-Subtractor + Explicit Low-Latency Mux**:
- Combined the **17-bit zero-extended unified comparator-subtractor** from Experiment 03 (`diff_ext = {1'b0, in0} - {1'b0, in1}`) with the **explicit bitwise AND/OR 3-input multiplexer logic** from Experiment 01 (`out = ({16{sel == 2'd0}} & in_$000) | ...`).
- **Functional & Equivalence Status**: Verified 100% equivalence (5/5 GCD directed tests passed; 165,802 comparator-subtractor arithmetic vectors passed with 0 errors).
- **Physical Verification**: 0 DRC violations, 0 unrouted nets, 0 hold violations, valid GDSII layout (891,468 bytes).

### Key Takeaways
1. **Area Reduction Retained**: Total standard-cell area was **4,755.81 µm²**, preserving almost the entirety of the area reduction achieved in Exp 03 (**-9.18% vs. Baseline [5,236.27 µm²]**, and **-3.77% vs. Exp 01 [4,942.24 µm²]**). Total standard-cell count reached **503**, the lowest count among all experiments.
2. **Setup Slack Did Not Recover**: Contrary to the hope that the explicit multiplexer would relieve timing, Setup WNS measured **-1.5115 ns** (compared to **-1.4911 ns** in Exp 03, **-1.3954 ns** in Baseline, and **-1.3625 ns** in Exp 01).
3. **Setup Violations Jumped Significantly**: Violating endpoints increased from **58** (Exp 03) to **84** (Exp 04) (+44.8%). Replicating the selector condition across all 16 bit-slices expanded the logic cone and capacitive fanout, pulling more register endpoints into setup violation.
4. **Output Path Slack Improved**: The worst path to the output port `resp_msg[15]` improved from **-1.46 ns** (Exp 03) to **-1.39 ns** (Exp 04).

---

## 2. Five-Way PPA Comparison Table

| Metric | Baseline | Exp 01 | Exp 02 | Exp 03 | Exp 04 | Exp 04 vs Base | Exp 04 vs Exp 01 | Exp 04 vs Exp 03 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Setup WNS (ns)** | -1.3954 | -1.3625 | -2.3619 | -1.4911 | **-1.5115** | -0.1161 (-8.3%) | -0.1490 (-10.9%) | -0.0204 (-1.4%) |
| **Setup TNS (ns)** | -62.6899 | -61.6748 | -72.5953 | -64.6083 | **-67.3086** | -4.6187 (-7.4%) | -5.6338 (-9.1%) | -2.7003 (-4.2%) |
| **Hold WNS (ns)** | +0.6141 | +0.6013 | +0.6352 | +0.4787 | **+0.4769** | -0.1372 (-22.3%) | -0.1244 (-20.7%) | -0.0018 (-0.4%) |
| **Hold TNS (ns)** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | **0.0000** | 0.0000 (0.0%) | 0.0000 (0.0%) | 0.0000 (0.0%) |
| **Fmax (MHz)** | 400.75 | 406.09 | 290.77 | 385.94 | **382.92** | -17.82 (-4.4%) | -23.17 (-5.7%) | -3.02 (-0.8%) |
| **Setup Violations** | 63 | 65 | 81 | **58** | **84** | **+21 (+33.3%)** | **+19 (+29.2%)** | **+26 (+44.8%)** |
| **Hold Violations** | 0 | 0 | 0 | 0 | **0** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Std-Cell Area (µm²)** | 5,236.27 | 4,942.24 | 4,523.09 | 4,748.30 | **4,755.81** | **-480.46 (-9.2%)** | **-186.43 (-3.8%)** | +7.51 (+0.2%) |
| **Core Utilization (%)** | 88.97 | 83.97 | 69.25 | 79.73 | **79.85** | -9.11% | -4.12% | +0.13% |
| **Total Instances** | 813 | 868 | 989 | 892 | **843** | +30 (+3.7%) | -25 (-2.9%) | -49 (-5.5%) |
| **Std-Cell Count** | 545 | 528 | 518 | 508 | **503** | **-42 (-7.7%)** | **-25 (-4.7%)** | **-5 (-1.0%)** |
| **Timing Repair Buffers** | 196 | 179 | 147 | 172 | **168** | **-28 (-14.3%)** | **-11 (-6.1%)** | -4 (-2.3%) |
| **Timing Repair Area (µm²)** | 1,741.67 | 1,552.74 | 1,333.78 | 1,475.16 | **1,503.94** | -237.73 (-13.6%) | -48.80 (-3.1%) | +28.78 (+2.0%) |
| **Estimated Total Power (mW)** | 9.292 | 8.404 | 6.706 | 8.308 | **8.405** | **-0.888 (-9.6%)** | +0.001 (+0.0%) | +0.097 (+1.2%) |
| **Internal Power (mW)** | 5.928 | 5.341 | 4.442 | 5.350 | **5.454** | -0.474 (-8.0%) | +0.112 (+2.1%) | +0.104 (+1.9%) |
| **Switching Power (mW)** | 3.364 | 3.062 | 2.264 | 2.959 | **2.951** | -0.413 (-12.3%) | -0.111 (-3.6%) | -0.008 (-0.3%) |
| **Leakage Power (µW)** | 0.0023 | 0.0022 | 0.0019 | 0.0021 | **0.0021** | -0.0002 (-8.5%) | -0.0001 (-4.5%) | -0.0000 (-1.1%) |
| **Route DRC Violations** | 0 | 0 | 0 | 0 | **0** | Clean | Clean | Clean |
| **GDS File Size (bytes)** | 870,412 | 869,456 | 869,992 | 870,300 | **891,468** | Valid stream | Valid stream | Valid stream |

---

## 3. Critical Path Progression Across All Experiments

| Run | Worst Path (Startpoint $\to$ Endpoint) | Slack | Path Description |
|---|---|:---:|---|
| **Baseline** | `dpath.b_reg.out[2] -> dpath.a_reg.out[3]` | -1.395 ns | Standalone comparator output into multiplexer selection |
| **Exp 01** | `dpath.b_reg.out[3] -> dpath.a_reg.out[9]` | -1.362 ns | Explicit AND/OR multiplexer path |
| **Exp 02** | `dpath.b_reg.out[1] -> dpath.a_reg.out[15]` | -2.340 ns | 15-bit linear ripple-borrow cascade |
| **Exp 03** | `dpath.b_reg.out[0] -> dpath.a_reg.out[0]` | -1.491 ns | 17-bit Han-Carlson parallel-prefix adder bit 0 subtraction & muxing |
| **Exp 04** | `dpath.b_reg.out[0] -> dpath.a_reg.out[10]` | -1.512 ns | 17-bit Han-Carlson carry MSB [16] into explicit mux bit 10 |

### Critical Path Analysis for Exp 04
In Experiment 04:
- **Startpoint**: `dpath.b_reg.out[0]$_DFFE_PP_/CLK` (clocked by `core_clock`)
- **Path Details**:
  - The launch clock arrives at `0.29 ns`.
  - The output of `b_reg[0]` launches into the 17-bit Han-Carlson adder tree (`ALU_16_0_16_0_17_unused_CO_X_HAN_CARLSON`), traversing gates `xor2_2`, `maj3_2`, `maj3_2`, `a21oi_2`, `o21ai_2`, `a21oi_4`, and `xnor2_4` to produce borrow bit `diff_ext[16]` at `2.17 ns`.
  - From `diff_ext[16]`, the signal is buffered by `place134` (`buf_12`) and enters the explicit multiplexer network for `a_reg[10]` (`mux2i_4` and `o21ai_1`), reaching `a_reg.out[10]/D` at `2.66 ns`.
- **Data Required**: `1.15 ns` (clock period `1.10 ns` + capture latency `0.29 ns` - setup time `0.24 ns`).
- **Setup Slack**: `1.15 ns - 2.66 ns =` **`-1.5115 ns`**.

---

## 4. Evaluation of the Composite Hypothesis

1. **Did Exp 04 improve WNS over Exp 03?**
   **No.** Setup WNS degraded by 20.4 ps (-1.5115 ns vs. -1.4911 ns).
2. **Did Exp 04 recover the timing performance of Exp 01?**
   **No.** Exp 04 remains 149.0 ps worse than Exp 01 (-1.5115 ns vs. -1.3625 ns).
3. **Did Exp 04 retain the area reduction from Exp 03?**
   **Yes.** Exp 04 achieved 4,755.81 µm², within 0.16% of Exp 03's area (4,748.30 µm²), retaining a **9.18% area reduction** compared to Baseline.
4. **Did setup violations improve?**
   **No.** Setup violations rose sharply from **58 to 84**. The explicit AND/OR structure distributed the selection logic into individual bit-level gates, increasing high-fanout nets and preventing OpenROAD from consolidating mux gates as effectively as in Exp 03.
5. **Conclusion**:
   Combining the explicit mux with the unified comparator-subtractor produces worse timing and higher violation counts than Exp 03 alone. **Experiment 03 remains the superior candidate.**

