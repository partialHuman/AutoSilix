# PPA Comparison: GCD Baseline vs. Experiment 01 vs. Experiment 02

## 1. Executive Summary

Experiment 02 replaced the inferred 16-bit Verilog subtractor (`out = in0 - in1`) in `Subtractor_0x422b1f52edd46a85` with an explicit bit-level ripple-borrow subtractor chain.

### Key Findings
1. **Timing Degraded Severely**: Setup WNS degraded by **-0.9665 ns (-69.3%)** relative to baseline (from -1.3954 ns to -2.3619 ns). Fmax dropped from **400.75 MHz to 290.77 MHz (-27.4%)**.
2. **Setup Violations Rose**: Violations increased from 63 to 81 (+28.6%).
3. **Standard-Cell Area Decreased Significantly**: Cell area decreased by **-713.18 µm² (-13.6%)** vs. baseline and by **-419.15 µm² (-8.5%)** vs. Exp 01.
4. **Estimated Power Dropped**: Total estimated power dropped by **-2.59 mW (-27.8%)** vs. baseline (from 9.29 mW to 6.71 mW).
5. **Physical Implementation Remained Clean**: Detailed routing completed with **0 DRC violations** and layout stream (GDSII) generated cleanly (869,992 bytes).

---

## 2. PPA Comparative Results Table

| Metric | Baseline (Inferred Sub) | Experiment 01 (Explicit Mux) | Experiment 02 (Ripple Sub) | Exp02 vs Baseline | Exp02 vs Exp01 |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Setup WNS (ns)** | -1.3954 | -1.3625 | **-2.3619** | -0.9665 (-69.3%) | -0.9994 (-73.3%) |
| **Setup TNS (ns)** | -62.6899 | -61.6748 | **-72.5953** | -9.9054 (-15.8%) | -10.9205 (-17.7%) |
| **Hold WNS (ns)** | +0.6141 | +0.6013 | **+0.6352** | +0.0210 (+3.4%) | +0.0339 (+5.6%) |
| **Hold TNS (ns)** | 0.0000 | 0.0000 | **0.0000** | 0.0000 (0.0%) | 0.0000 (0.0%) |
| **Fmax (MHz)** | 400.75 | 406.09 | **290.77** | -109.97 (-27.4%) | -115.32 (-28.4%) |
| **Setup Violations** | 63 | 65 | **81** | +18 (+28.6%) | +16 (+24.6%) |
| **Hold Violations** | 0 | 0 | **0** | 0 (0.0%) | 0 (0.0%) |
| **Std-Cell Area (µm²)** | 5,236.27 | 4,942.24 | **4,523.09** | -713.18 (-13.6%) | -419.15 (-8.5%) |
| **Core Utilization (%)** | 88.97 | 83.97 | **69.25** | -19.71% | -14.72% |
| **Total Instances** | 813 | 868 | **989** | +176 (+21.6%) | +121 (+13.9%) |
| **Std-Cell Instances** | 545 | 528 | **518** | -27 (-5.0%) | -10 (-1.9%) |
| **Timing Repair Buffers** | 196 | 179 | **147** | -49 (-25.0%) | -32 (-17.9%) |
| **Timing Repair Area (µm²)**| 1,741.67 | 1,552.74 | **1,333.78** | -407.89 (-23.4%) | -218.96 (-14.1%) |
| **Estimated Total Power (mW)**| 9.292 | 8.404 | **6.706** | -2.587 (-27.8%) | -1.698 (-20.2%) |
| **Internal Power (mW)** | 5.928 | 5.341 | **4.442** | -1.486 (-25.1%) | -0.900 (-16.8%) |
| **Switching Power (mW)**| 3.364 | 3.062 | **2.264** | -1.101 (-32.7%) | -0.798 (-26.1%) |
| **Leakage Power (µW)** | 0.0023 | 0.0022 | **0.0019** | -0.0003 (-15.2%) | -0.0003 (-11.5%) |
| **Route DRC Violations**| 0 | 0 | **0** | Clean | Clean |
| **GDS File Size (bytes)**| 870,412 | 869,456 | **869,992** | Clean | Clean |

---

## 3. Critical Path Shift Analysis

### Baseline Critical Path
- **Startpoint**: `dpath.b_reg.out[2]$_DFFE_PP_`
- **Endpoint**: `dpath.a_reg.out[3]$_DFFE_PP_`
- **Slack**: `-1.395 ns`
- **Mechanism**: Combined datapath comparison and multiplexer propagation.

### Experiment 02 Critical Path
- **Startpoint**: `dpath.b_reg.out[1]$_DFFE_PP_`
- **Endpoint**: `dpath.a_reg.out[15]$_DFFE_PP_`
- **Data Arrival Time**: `3.49 ns`
- **Data Required Time**: `1.15 ns`
- **Slack**: `-2.34 ns` (Global WNS `-2.3619 ns`)
- **Mechanism**: The 15-bit ripple-borrow chain. The carry/borrow signal propagates sequentially from bit 1 up to bit 15 through a cascading series of compound gates (`sky130_fd_sc_hd__o21ai_2`, `a31oi_2`, `o31ai_2`, `a221oi_4`, `xnor2_2`, `mux2i_1`, `o21ai_1`). Each stage adds ~0.10 - 0.25 ns of delay, preventing synthesis from restructuring the logic into a tree.

---

## 4. Conclusion and Architectural Recommendation

The explicit 16-bit ripple-borrow subtractor **demonstrates a clear Pareto trade-off**:
- **Area & Power Advantage**: Standard-cell area fell by 13.6% and power fell by 27.8%.
- **Timing Disadvantage**: Worst negative slack worsened by 69.3%, moving the design much further away from closing timing at the 1.10 ns target.

**Retention Decision**: Retain Experiment 02 as a **negative timing result / positive area result**. It should **not** be chosen as the candidate baseline for performance-driven closure, but its findings provide clear proof that the arithmetic subtractor is directly on the critical timing path.

