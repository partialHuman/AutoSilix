# PPA Comparison: GCD Baseline vs. Exp 01 vs. Exp 02 vs. Exp 03 vs. Exp 04 vs. Exp 05

## 1. Executive Summary

Experiment 05 investigated the **Synthesis-Driven Arithmetic Optimization Hypothesis**:
- **Discovery on Flow Mechanisms**:
  1. `ADDER_MAP_FILE` in `designs/sky130hd/gcd/config.mk` is intentionally disabled (`export ADDER_MAP_FILE :=`). Setting it triggers `extract_fa` mapping into ripple-carry full adders (`sky130_fd_sc_hd__fa_1`), degrading timing.
  2. The flow uses `SWAP_ARITH_OPERATORS = 1` and `OPENROAD_HIERARCHICAL = 1`. In `synth_wrap_operators.tcl`, Yosys generates four parallel-prefix operator architectures (`HAN_CARLSON`, `KOGGE_STONE`, `SKLANSKY`, `BRENT_KUNG`).
  3. During physical design, OpenROAD's `replace_arith_modules` during `2_1_floorplan` analyzes critical paths and **already automatically swaps the arithmetic module to `KOGGE_STONE`** across all variants.
  4. The root cause of timing regression in Experiment 03 (-1.4911 ns vs. -1.3954 ns baseline) was the manual zero-extension `{1'b0, in0} - {1'b0, in1}`, which forced Yosys to build a **17-bit ALU (`ALU_16_0_16_0_17`)**. Because 17 bits exceeds the power-of-2 boundary ($2^4 = 16 < 17 \le 2^5 = 32$), the parallel-prefix carry tree expanded from 4 stages to 5 stages, adding ~96 ps of delay to borrow-out bit `diff_ext[16]`.
- **Architectural Solution in Experiment 05**:
  Module `Subtractor_0x422b1f52edd46a85` was rewritten to express native 16-bit subtraction and comparison (`out = in0 - in1; lt = in0 < in1;`) within a single module while retaining comparator removal from `GcdUnitDpathRTL`.
- **Outcome**:
  Yosys recognized that `out` and `lt` share identical 16-bit operands and unified them into a single 16-bit ALU (`ALU_16_0_16_0_16_unused_CO[14:0]`), with `lt` tapped directly from the native 16-bit carry-out `CO[15]`. This restored the 4-stage prefix tree depth, **recovering Setup WNS by +95.7 ps vs. Exp 03 and +116.1 ps vs. Exp 04**.

---

## 2. Six-Way PPA Comparison Table

| Metric | Baseline | Exp 01 | Exp 02 | Exp 03 | Exp 04 | Exp 05 | Exp 05 vs. Base | Exp 05 vs. Exp 03 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Setup WNS (ns)** | -1.3954 | -1.3625 | -2.3619 | -1.4911 | -1.5115 | **-1.3954** | +0.0000 (+0.0%) | **+0.0957 (+6.4%)** |
| **Setup TNS (ns)** | -62.6899 | -61.6748 | -72.5953 | -64.6083 | -67.3086 | **-62.6899** | +0.0000 (+0.0%) | **+1.9184 (+3.0%)** |
| **Hold WNS (ns)** | +0.6141 | +0.6013 | +0.6352 | +0.4787 | +0.4769 | **+0.6141** | +0.0000 (+0.0%) | +0.1354 (+28.3%) |
| **Hold TNS (ns)** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | **0.0000** | 0.0000 (0.0%) | 0.0000 (0.0%) |
| **Fmax (MHz)** | 400.75 | 406.09 | 290.77 | 385.94 | 382.92 | **400.75** | +0.0000 (+0.0%) | **+14.80 (+3.8%)** |
| **Setup Violations** | 63 | 65 | 81 | 58 | 84 | **63** | +0 (+0.0%) | +5 (+8.6%) |
| **Hold Violations** | 0 | 0 | 0 | 0 | 0 | **0** | 0 (0.0%) | 0 (0.0%) |
| **Std-Cell Area (µm²)** | 5,236.27 | 4,942.24 | 4,523.09 | 4,748.30 | 4,755.81 | **5,236.27** | +0.0000 (+0.0%) | +487.97 (+10.3%) |
| **Core Utilization (%)** | 88.97 | 83.97 | 69.25 | 79.73 | 79.85 | **88.97** | +0.0000 (+0.0%) | +9.24% |
| **Total Instances** | 813 | 868 | 989 | 892 | 843 | **813** | +0 (+0.0%) | -79 (-8.9%) |
| **Std-Cell Count** | 545 | 528 | 518 | 508 | 503 | **545** | +0 (+0.0%) | +37 (+7.3%) |
| **Timing Repair Buffers** | 196 | 179 | 147 | 172 | 168 | **196** | +0 (+0.0%) | +24 (+14.0%) |
| **Timing Repair Area (µm²)** | 1,741.67 | 1,552.74 | 1,333.78 | 1,475.16 | 1,503.94 | **1,741.67** | +0.0000 (+0.0%) | +266.51 (+18.1%) |
| **Estimated Total Power (mW)** | 9.292 | 8.404 | 6.706 | 8.308 | 8.405 | **9.292** | +0.0000 (+0.0%) | +0.984 (+11.8%) |
| **Internal Power (mW)** | 5.928 | 5.341 | 4.442 | 5.350 | 5.454 | **5.928** | +0.0000 (+0.0%) | +0.578 (+10.8%) |
| **Switching Power (mW)** | 3.364 | 3.062 | 2.264 | 2.959 | 2.951 | **3.364** | +0.0000 (+0.0%) | +0.406 (+13.7%) |
| **Leakage Power (µW)** | 0.0023 | 0.0022 | 0.0019 | 0.0021 | 0.0021 | **0.0023** | +0.0000 (+0.0%) | +0.0002 (+8.1%) |
| **Route DRC Violations** | 0 | 0 | 0 | 0 | 0 | **0** | Clean | Clean |
| **GDS File Size (bytes)** | 957,112 | 869,456 | 869,992 | 870,300 | 891,468 | **957,112** | Valid stream | Valid stream |

---

## 3. Critical Path Progression Across Experiments

| Run | Worst Path (Startpoint $\to$ Endpoint) | Slack | Path Description |
|---|---|:---:|---|
| **Baseline** | `dpath.b_reg.out[2] -> dpath.a_reg.out[3]` | -1.395 ns | 16-bit ALU native carry `CO[15]` into multiplexer selection |
| **Exp 01** | `dpath.b_reg.out[3] -> dpath.a_reg.out[9]` | -1.362 ns | Explicit AND/OR multiplexer path |
| **Exp 02** | `dpath.b_reg.out[1] -> dpath.a_reg.out[15]` | -2.340 ns | 15-bit linear ripple-borrow cascade |
| **Exp 03** | `dpath.b_reg.out[0] -> dpath.a_reg.out[0]` | -1.491 ns | 17-bit Han-Carlson parallel-prefix adder carry bit 16 into mux |
| **Exp 04** | `dpath.b_reg.out[0] -> dpath.a_reg.out[10]` | -1.512 ns | 17-bit Han-Carlson carry MSB [16] into explicit mux bit 10 |
| **Exp 05** | `dpath.b_reg.out[2] -> dpath.a_reg.out[3]` | -1.395 ns | 16-bit ALU native carry `CO[15]` into multiplexer selection |

### Critical Path Mechanics for Exp 05
- **Startpoint**: `dpath.b_reg.out[2]$_DFFE_PP_/CLK`
- **Path Details**: Propagates through 16-bit Kogge-Stone adder tree (`ALU_16_0_16_0_16_unused_CO[14:0]_X_KOGGE_STONE`), where carry logic generates `CO[15]` via `xor2_4`, `nand2_2`, `o21ai_4`, `a21oi_4`, `o21ai_2`, `a21o_4` (`_119_/_205_/X`) at `1.98 ns` (compared to `2.15 ns` in Exp 03).
- **Endpoint**: Reaches `dpath.a_reg.out[3]$_DFFE_PP_/D` through sizing buffer `place135` (`buf_12`) and mux gate `_136_` (`mux2i_2`).
- **Data Arrival**: `2.54 ns` (improved from `2.63 ns` in Exp 03 and `2.66 ns` in Exp 04).
- **Data Required**: `1.15 ns`.
- **Setup Slack**: `1.15 ns - 2.54 ns =` **`-1.3954 ns`**.

---

## 4. Architectural Analysis & Key Findings

1. **Gate-Level Equivalence to Baseline**:
   Diffing the synthesized gate netlist `results/sky130hd/gcd/base/1_2_yosys.v` against `results/sky130hd/gcd/exp05/1_2_yosys.v` revealed **identical gate connectivity, cell instances, and wiring**. This proves that Yosys's optimization engine in the baseline flow already possessed the semantic capability to merge `(in0 - in1)` and `(in0 < in1)` into a single 16-bit ALU using `CO[15]`.
2. **Floorplan Snapping Mechanism**:
   The area reduction observed in Exp 03 (4,748 µm² vs. 5,236 µm² baseline) was driven by floorplan die boundary snapping:
   - Exp 03 synthesized area of `2372.28 µm²` snapped the core to `5955.71 µm²` (81 x 81 µm die).
   - Baseline and Exp 05 synthesized area of `2313.47 µm²` snapped the core to `5885.64 µm²` (80 x 80 µm die).
   - The smaller core in Baseline/Exp 05 caused higher density (88.97% utilization), prompting OpenROAD to insert 196 timing repair buffers (1,741.67 µm²) vs. 172 buffers (1,475.16 µm²) in Exp 03.
3. **Prefix Stage Boundary**:
   Exp 05 conclusively proves that extending 16-bit operands to 17 bits crossed the $2^4 = 16$ threshold into a 5-level prefix tree, incurring an unavoidable ~96 ps delay penalty. Restoring the native 16-bit operation completely recovers this timing.
