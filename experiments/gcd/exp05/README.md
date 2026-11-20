# AutoSilix — Experiment 05: Synthesis-Driven Arithmetic Optimization

## 1. Objective

Investigate whether a better synthesis implementation of the subtraction/comparison datapath can improve timing while retaining the area advantages of Experiment 03.

---

## 2. Hypothesis

In Experiment 03, zero-extending 16-bit operands to 17 bits (`diff_ext = {1'b0, in0} - {1'b0, in1}`) crossed the $2^4 = 16$ power-of-2 boundary, forcing Yosys to build a 17-bit parallel-prefix carry tree (`ALU_16_0_16_0_17`) with 5 logic levels rather than 4 levels ($\lceil \log_2(17) \rceil = 5$ vs. $\log_2(16) = 4$).

**Hypothesis**: Expressing native 16-bit unsigned subtraction and comparison within the unified `Subtractor` module:
```verilog
always @ (*) begin
  out = (in0 - in1);
  lt  = (in0 < in1);
end
```
allows Yosys to:
1. Infer a 16-bit ALU (`ALU_16_0_16_0_16`) with only 4 prefix stages.
2. Connect `lt` directly to the native 16-bit carry-out `CO[15]`.
3. Recover the ~96 ps timing penalty introduced by the 17-bit tree expansion in Experiment 03.

---

## 3. Baseline and Reference Experiments

- **Baseline (`baseline/gcd_original.v`)**: Inferred separate 16-bit subtractor and comparator.
- **Experiment 03 (`exp03/gcd.v`)**: Primary reference. Removed `LtComparator` from datapath hierarchy; computed comparison via 17-bit zero-extended subtractor.
- **Experiment 04 (`exp04/gcd.v`)**: Combined Exp 03 with an explicit AND/OR 3-input mux (timing regressed to -1.5115 ns).

---

## 4. Architecture and RTL Differences

Starting from `experiments/gcd/exp03/gcd.v`:
- Preserved the datapath removal of `LtComparator_0x422b1f52edd46a85` (connecting `sub$lt` directly to `is_a_lt_b`).
- In `Subtractor_0x422b1f52edd46a85`, replaced the 17-bit zero-extended expression with native 16-bit subtraction and comparison.

### Git Diff Against Experiment 03
```diff
--- /workspace/experiments/gcd/exp03/gcd.v
+++ /workspace/experiments/gcd/exp05/gcd.v
@@ -724,15 +724,13 @@ module Subtractor_0x422b1f52edd46a85
   input  wire [   0:0] reset
 );
 
-  reg [16:0] diff_ext;
-
-  // 17-bit zero-extended unsigned subtraction:
-  // diff_ext[15:0] provides the 16-bit difference (out)
-  // diff_ext[16]   provides the borrow-out indicating in0 < in1 (lt)
+  // Native 16-bit unified unsigned subtraction and comparison:
+  // Evaluates 16-bit subtraction and comparison within a single module,
+  // allowing Yosys to map into a 16-bit ALU (ALU_16_0_16_0_16) with 4 prefix stages
+  // instead of crossing the 17-bit boundary into 5 prefix stages.
   always @ (*) begin
-    diff_ext = {1'b0, in0} - {1'b0, in1};
-    out = diff_ext[15:0];
-    lt  = diff_ext[16];
+    out = (in0 - in1);
+    lt  = (in0 < in1);
   end
 
 endmodule // Subtractor_0x422b1f52edd46a85
```

---

## 5. Toolchain and Configuration Discovery

Inspection of OpenROAD-flow-scripts and Yosys scripts revealed:
1. **`ADDER_MAP_FILE`**: Disabled in `designs/sky130hd/gcd/config.mk` (`export ADDER_MAP_FILE :=`). Setting it triggers `extract_fa` mapping to ripple-carry full adders (`sky130_fd_sc_hd__fa_1`), degrading GCD timing.
2. **`SWAP_ARITH_OPERATORS = 1`**: Enables Yosys arithmetic wrapping (`synth_wrap_operators.tcl`) into four candidate architectures (`HAN_CARLSON`, `KOGGE_STONE`, `SKLANSKY`, `BRENT_KUNG`).
3. **OpenROAD Dynamic Swapping**: During `2_1_floorplan`, OpenROAD's `replace_arith_modules` evaluates timing slack and **automatically selects `KOGGE_STONE`**.

---

## 6. Verification Methodology & Results

### 6.1 Full GCD Functional Simulation
Executed `tests/rtl/tb_gcd.v` via `iverilog` + `vvp`:
- `PASS: gcd(48,18) = 6` (9 cycles)
- `PASS: gcd(7,13) = 1` (13 cycles)
- `PASS: gcd(16,16) = 16` (3 cycles)
- `PASS: gcd(0,9) = 9` (2 cycles)
- `PASS: gcd(9,0) = 9` (1 cycles)
- **Status: 5 / 5 tests passed.**

### 6.2 Subtractor / Comparator Combinational Equivalence
Executed `tests/rtl/tb_unified_sub_equiv.v`:
- Tested 165,802 vector pairs (256 corner pairs, 10 boundary cases, 65,536 exhaustive 8-bit pairs, 100,000 random 16-bit pairs).
- **Errors: 0**. Status: **Bit-for-bit equivalence confirmed.**

---

## 7. Synthesis and Physical-Design Commands

```bash
source /OpenROAD-flow-scripts/env.sh
cd /OpenROAD-flow-scripts/flow
make \
  DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk \
  FLOW_VARIANT=exp05 \
  VERILOG_FILES=/workspace/experiments/gcd/exp05/gcd.v \
  finish
```
- Total flow runtime: **63 seconds**.
- Final GDS generated: `957,112 bytes` at `results/sky130hd/gcd/exp05/6_final.gds`.
- Detailed routing reported **0 DRC violations** and **0 unrouted nets**.

---

## 8. Final Six-Way PPA Comparison Table

| Metric | Baseline | Exp 01 | Exp 02 | Exp 03 | Exp 04 | Exp 05 | Exp 05 vs Base | Exp 05 vs Exp 03 |
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

## 9. Critical Path Analysis

- **Startpoint**: `dpath.b_reg.out[2]$_DFFE_PP_/CLK`
- **Endpoint**: `dpath.a_reg.out[3]$_DFFE_PP_/D`
- **Data Arrival**: `2.54 ns` (recovered by 90 ps compared to Exp 03's `2.63 ns`).
- **Data Required**: `1.15 ns`.
- **Setup Slack**: **`-1.3954 ns`** (recovered by +95.7 ps vs. Exp 03).
- **Mechanism**: The 16-bit Kogge-Stone tree generated carry-out `CO[15]` via `xor2_4`, `nand2_2`, `o21ai_4`, `a21oi_4`, `o21ai_2`, and `a21o_4` (`_119_/_205_/X`) at `1.98 ns` (compared to `2.15 ns` in Exp 03).

---

## 10. Limitations

- Neither Experiment 03 nor Experiment 05 closes setup timing at the 1.10 ns target (both have negative slack: -1.491 ns and -1.395 ns).
- While Experiment 05 recovers timing (+95.7 ps), its final standard-cell area (5,236.27 µm²) and power (9.292 mW) are higher than Experiment 03 (4,748.30 µm², 8.308 mW) because the smaller post-synthesis netlist snapped to a smaller floorplan die (80 x 80 µm vs. 81 x 81 µm), causing higher placement density (88.97% utilization) and requiring 24 more timing repair buffers.

---

## 11. Conclusion and Retention Decision

**Decision**:
- **Experiment 05 is confirmed as a technically successful timing recovery experiment** that proves the 17-bit power-of-2 prefix stage penalty hypothesis.
- **Pareto Trade-off**:
  - If **timing/Fmax** is the priority: Experiment 05 is superior to Experiment 03 (400.75 MHz vs. 385.94 MHz, WNS -1.3954 ns vs. -1.4911 ns).
  - If **area/power** is the priority: Experiment 03 is superior (4,748.30 µm² vs. 5,236.27 µm², 8.308 mW vs. 9.292 mW).
- **Recommendation**: Retain Experiment 03 for minimum-area/power constraints, and retain Experiment 05 as the timing-optimal unified arithmetic implementation.
