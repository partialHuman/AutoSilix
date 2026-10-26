# AutoSilix — Experiment 04: Unified Comparator-Subtractor + Explicit Mux

## 1. Experiment Overview

- **Design**: `gcd`
- **PDK / Platform**: `sky130hd`
- **Flow Variant**: `exp04`
- **Clock Target**: `1.10 ns` (909 MHz target)
- **RTL SHA-256 (Exp04)**: `7d6730977a5d9d2e09a13485fed1557e201b89d7c2a7722808bcf5a55b0f8f7b`
- **RTL SHA-256 (Exp03)**: `9175f15513c0705c44786cdb2c26fbc7bee9625e465db785ddd21c07d9086a4c`
- **RTL SHA-256 (Exp02)**: `e7bcbbd3a25d13cba2690a02d8063ca4b14fa05ca5e667991872fa3aedb31185`
- **RTL SHA-256 (Exp01)**: `4ba5f51ebd075c71f6f4fef8414581b199e26826147851cb3b5e67c643d3662f`
- **RTL SHA-256 (Baseline)**: `7330ee37a6d4f8ab6ad4b5829a35a347c996ac32e1cfcd052352ecff2705eb91`

### Objective
Investigate whether combining the **unified 17-bit zero-extended comparator-subtractor** from Experiment 03 with the **explicit 3-input multiplexer logic** from Experiment 01 improves timing slack (WNS/TNS) while retaining the standard-cell area and power reductions achieved in Experiment 03.

---

## 2. RTL Modification

Starting from `/workspace/experiments/gcd/exp03/gcd.v`, exactly one modification was made:
- Module `Mux_0x683fa1a418b072c9` (the 3-input multiplexer `a_mux` selecting between `req_msg_a`, `sub_out`, and `b_reg_out`) was updated from the indexed syntax `out = in_[sel];` to explicit AND/OR bitwise selection logic:
  ```verilog
  out = ({16{sel == 2'd0}} & in_$000)
      | ({16{sel == 2'd1}} & in_$001)
      | ({16{sel == 2'd2}} & in_$002);
  ```

All other structures—including the 2-input multiplexer `Mux_0xdd6473406d1a99a`, the unified 17-bit comparator-subtractor `Subtractor_0x422b1f52edd46a85`, controller states, registers, and resets—remained identical to Experiment 03.

### Git Diff Against Experiment 03
```diff
--- /workspace/experiments/gcd/exp03/gcd.v
+++ /workspace/experiments/gcd/exp04/gcd.v
@@ -661,7 +661,9 @@ module Mux_0x683fa1a418b072c9
 
   // logic for comb_logic()
   always @ (*) begin
-    out = in_[sel];
+    out = ({16{sel == 2'd0}} & in_$000)
+        | ({16{sel == 2'd1}} & in_$001)
+        | ({16{sel == 2'd2}} & in_$002);
   end
```

---

## 3. Verification Commands & Results

### 3.1 Full GCD Functional Simulation
```bash
iverilog -g2012 -s tb_gcd \
  -o /tmp/tb_gcd_exp04 \
  /workspace/experiments/gcd/exp04/gcd.v \
  /workspace/tests/rtl/tb_gcd.v
vvp /tmp/tb_gcd_exp04
```
**Results**:
- `PASS: gcd(48,18) = 6` (9 cycles)
- `PASS: gcd(7,13) = 1` (13 cycles)
- `PASS: gcd(16,16) = 16` (3 cycles)
- `PASS: gcd(0,9) = 9` (2 cycles)
- `PASS: gcd(9,0) = 9` (1 cycles)
- **Status: 5 / 5 test cases completed successfully.**

### 3.2 Unified Comparator-Subtractor Combinational Equivalence
```bash
iverilog -g2012 -s tb_unified_sub_equiv \
  -o /tmp/tb_unified_sub_equiv_exp04 \
  /workspace/experiments/gcd/exp04/gcd.v \
  /workspace/tests/rtl/tb_unified_sub_equiv.v
vvp /tmp/tb_unified_sub_equiv_exp04
```
**Results**:
- 256 edge cross-product tests
- 10 targeted boundary cases
- 65,536 exhaustive 8-bit subspace vectors ([0..255] × [0..255])
- 100,000 randomized 16-bit vectors
- **Total Vectors Tested: 165,802**
- **Errors: 0**
- Status: **Bit-for-bit equivalence confirmed.**

---

## 4. Synthesis & Physical-Design Implementation

### 4.1 Synthesis Observations
- **Comparator Status**: Standalone `LtComparator_0x422b1f52edd46a85` remains **completely absent** from the netlist.
- **Arithmetic Logic**: Retains exactly one shared 17-bit arithmetic operator:
  `ALU_16_0_16_0_17_unused_CO_X_HAN_CARLSON \dpath.sub.diff_ext\ALU_16_0_16_0_17_unused_CO_X_HAN_CARLSON`
- **Mux Mapping**: The explicit AND/OR formulation mapped into compound gates (`mux2_1`, `mux2i_4`, `o21ai_0`, `nand2_1`, `or2_0`), altering gate pin assignments and buffer placement.

### 4.2 Physical-Design Execution
Executed full flow inside the Docker container:
```bash
source /OpenROAD-flow-scripts/env.sh
cd /OpenROAD-flow-scripts/flow
make \
  DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk \
  FLOW_VARIANT=exp04 \
  VERILOG_FILES=/workspace/experiments/gcd/exp04/gcd.v \
  finish
```
- Total flow runtime: **40 seconds**.
- Final GDS generated: `891,468 bytes` at `results/sky130hd/gcd/exp04/6_final.gds`.
- Detailed routing reported **0 DRC violations** and **0 unrouted nets**.

---

## 5. Five-Way PPA Comparison Table

| Metric | Baseline | Exp 01 | Exp 02 | Exp 03 | Exp 04 | Delta vs. Base | Delta vs. Exp 01 | Delta vs. Exp 03 |
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

---

## 6. Critical Path Analysis

### Worst Register-to-Register Path
- **Startpoint**: `dpath.b_reg.out[0]$_DFFE_PP_/CLK`
- **Endpoint**: `dpath.a_reg.out[10]$_DFFE_PP_/D`
- **Data Arrival**: `2.66 ns`
- **Data Required**: `1.15 ns`
- **Setup Slack**: **`-1.5115 ns`**
- **Traversed Gates**: `b_reg[0]` launches into Han-Carlson parallel-prefix tree (`xor2_2` -> `maj3_2` -> `maj3_2` -> `a21oi_2` -> `o21ai_2` -> `a21oi_4` -> `xnor2_4`) generating carry MSB `diff_ext[16]`, passes through sizing buffer `place134` (`buf_12`), then enters explicit multiplexer gates `_170_` (`mux2i_4`) and `_172_` (`o21ai_1`) before capturing at `a_reg[10]`.

### Comparison with Prior Experiments
- In **Exp 01**, the explicit mux alone improved WNS by +33 ps because it did not interact with the 17-bit extended adder carry tree.
- In **Exp 03**, the unified subtractor created a new critical path at bit 0 (-1.491 ns) due to the 17th carry bit, but dropped total violations to 58.
- In **Exp 04**, combining the explicit mux with the unified subtractor forced the explicit bitwise decode gates to fan out directly from the adder carry output across all 16 bits. This increased capacitive loading and degraded WNS by 20.4 ps, while ballooning violating endpoints from 58 to 84.

---

## 7. Retention Decision

**Decision**: **Reject Experiment 04 as a production candidate. Retain Experiment 03 as the premier design.**
- **Timing**: Exp 04 shows inferior timing compared to both Exp 01 (-1.5115 ns vs. -1.3625 ns) and Exp 03 (-1.5115 ns vs. -1.4911 ns).
- **Endpoints**: Setup violations rose sharply from 58 to 84 (+44.8%).
- **Area/Power**: Although Exp 04 retains low area (4,755.81 µm²) and power (8.405 mW), Experiment 03 achieves virtually the same area (4,748.30 µm²) and slightly lower power (8.308 mW) with significantly fewer timing violations (58 vs 84).

---

## 8. Next Recommended Experiment (Experiment 05)

### Proposed Optimization: Arithmetic Architecture Exploration via OpenROAD Adder Mapping
The critical timing bottleneck across Experiments 02, 03, and 04 remains the parallel-prefix adder structure (`ALU_16_0_16_0_17_unused_CO_X_HAN_CARLSON`).

- In OpenROAD/ORFS, the configuration variable `ADDER_MAP_FILE` controls the parallel-prefix adder generator in Yosys (`yosys/techlibs/common/openroad_adder.v`), selecting between:
  1. `KOGGE_STONE` (Lowest logic depth $\sim \log_2 N$, highest wiring density)
  2. `BRENT_KUNG` (Higher depth $\sim 2\log_2 N$, minimum area/fanout)
  3. `SKLANSKY` (Balanced depth, moderate fanout)
  4. `HAN_CARLSON` (Default hybrid used in Baseline, Exp 01, Exp 03, Exp 04)
- **Hypothesis for Exp 05**: Keeping the winning RTL from Experiment 03 (unified 17-bit subtractor + inferred clean mux), configure ORFS to target a **Kogge-Stone** parallel-prefix adder architecture to reduce logic stages along the carry chain, targeting setup timing recovery below -1.30 ns.

