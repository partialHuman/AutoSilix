# AutoSilix — Experiment 02: 16-Bit Ripple-Borrow Subtractor PPA Optimization

## 1. Experiment Overview

- **Design**: `gcd`
- **PDK / Platform**: `sky130hd`
- **Flow Variant**: `exp02`
- **Clock Target**: `1.10 ns` (909 MHz target)
- **RTL SHA-256 (Exp02)**: `e7bcbbd3a25d13cba2690a02d8063ca4b14fa05ca5e667991872fa3aedb31185`
- **RTL SHA-256 (Baseline)**: `7330ee37a6d4f8ab6ad4b5829a35a347c996ac32e1cfcd052352ecff2705eb91`

### Objective
Investigate whether implementing an explicit 16-bit ripple-borrow subtractor improves GCD design PPA compared to the inferred Verilog subtraction operator (`out = in0 - in1`) in module `Subtractor_0x422b1f52edd46a85`.

---

## 2. RTL Modification

Only the body of module `Subtractor_0x422b1f52edd46a85` in `exp02/gcd.v` was modified. All port definitions, widths, reset/clock signals, and other modules were preserved without alteration.

```verilog
module Subtractor_0x422b1f52edd46a85
(
  input  wire [   0:0] clk,
  input  wire [  15:0] in0,
  input  wire [  15:0] in1,
  output reg  [  15:0] out,
  input  wire [   0:0] reset
);

  wire [16:0] borrow;
  wire [15:0] diff;

  assign borrow[0] = 1'b0;

  genvar i;
  generate
    for (i = 0; i < 16; i = i + 1) begin : gen_sub
      assign diff[i] = in0[i] ^ in1[i] ^ borrow[i];

      assign borrow[i+1] =
        (~in0[i] & in1[i]) |
        (~(in0[i] ^ in1[i]) & borrow[i]);
    end
  endgenerate

  always @(*) begin
    out = diff;
  end

endmodule
```

### Git Diff Against Baseline
```diff
--- /workspace/experiments/gcd/baseline/gcd_original.v
+++ /workspace/experiments/gcd/exp02/gcd.v
@@ -741,15 +741,24 @@
-  // logic for comb_logic()
-  always @ (*) begin
-    out = (in0-in1);
+  wire [16:0] borrow;
+  wire [15:0] diff;
+
+  assign borrow[0] = 1'b0;
+
+  genvar i;
+  generate
+    for (i = 0; i < 16; i = i + 1) begin : gen_sub
+      assign diff[i] = in0[i] ^ in1[i] ^ borrow[i];
+
+      assign borrow[i+1] =
+        (~in0[i] & in1[i]) |
+        (~(in0[i] ^ in1[i]) & borrow[i]);
+    end
+  endgenerate
+
+  always @(*) begin
+    out = diff;
   end
```

---

## 3. Verification Commands & Results

### 3.1 Functional Simulation
```bash
iverilog -g2012 -s tb_gcd \
  -o /tmp/tb_gcd_exp02 \
  /workspace/experiments/gcd/exp02/gcd.v \
  /workspace/tests/rtl/tb_gcd.v
vvp /tmp/tb_gcd_exp02
```
**Results**:
- `PASS: gcd(48,18) = 6` (9 cycles)
- `PASS: gcd(7,13) = 1` (13 cycles)
- `PASS: gcd(16,16) = 16` (3 cycles)
- `PASS: gcd(0,9) = 9` (2 cycles)
- `PASS: gcd(9,0) = 9` (1 cycles)
- **5 / 5 test cases completed successfully.**

### 3.2 Combinational Equivalence Verification
```bash
iverilog -g2012 -s tb_subtractor_equiv \
  -o /tmp/tb_sub_equiv \
  /workspace/experiments/gcd/exp02/gcd.v \
  /workspace/tests/rtl/tb_subtractor_equiv.v
vvp /tmp/tb_sub_equiv
```
**Results**:
- Tests executed: 65,609
- Errors: 0
- Status: **Bit-for-bit combinational equivalence confirmed.**

---

## 4. ORFS Physical-Design Implementation

Command executed inside Docker container:
```bash
source /OpenROAD-flow-scripts/env.sh
cd /OpenROAD-flow-scripts/flow
make \
  DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk \
  FLOW_VARIANT=exp02 \
  VERILOG_FILES=/workspace/experiments/gcd/exp02/gcd.v \
  finish
```

Execution completed in 70s without errors. Final GDS generated: `869,992 bytes`. Detailed routing reported **0 DRC violations**.

---

## 5. PPA Summary & Interpretation

| Metric | Baseline | Exp 01 | Exp 02 | Delta vs. Baseline | Delta vs. Exp 01 |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Setup WNS (ns)** | -1.3954 | -1.3625 | **-2.3619** | -0.9665 (-69.3%) | -0.9994 (-73.3%) |
| **Setup TNS (ns)** | -62.6899 | -61.6748 | **-72.5953** | -9.9054 (-15.8%) | -10.9205 (-17.7%) |
| **Hold WNS (ns)** | +0.6141 | +0.6013 | **+0.6352** | +0.0210 (+3.4%) | +0.0339 (+5.6%) |
| **Fmax (MHz)** | 400.75 | 406.09 | **290.77** | -109.97 (-27.4%) | -115.32 (-28.4%) |
| **Setup Violations** | 63 | 65 | **81** | +18 (+28.6%) | +16 (+24.6%) |
| **Std-Cell Area (µm²)** | 5,236.27 | 4,942.24 | **4,523.09** | -713.18 (-13.6%) | -419.15 (-8.5%) |
| **Estimated Total Power (mW)** | 9.292 | 8.404 | **6.706** | -2.587 (-27.8%) | -1.698 (-20.2%) |
| **Timing Repair Buffers** | 196 | 179 | **147** | -49 (-25.0%) | -32 (-17.9%) |
| **Route DRC Violations** | 0 | 0 | **0** | Clean | Clean |

### Critical Path Analysis
In the baseline, the worst path was `dpath.b_reg.out[2] -> dpath.a_reg.out[3]` (slack: `-1.395 ns`).
In Experiment 02, the critical path shifted to a 15-bit linear borrow ripple from `dpath.b_reg.out[1]` to `dpath.a_reg.out[15]` (slack: `-2.34 ns`).

The explicit ripple structure forced OpenROAD to place a long serial cascade of 15 compound gates (`sky130_fd_sc_hd__o21ai_2`, `a31oi_2`, `o31ai_2`, `a221oi_4`), preventing ABC/Yosys from restructuring the logic into an optimized logarithmic carry-lookahead or prefix tree.

---

## 6. Retention Decision

**Retain Experiment 02 as an informative negative timing result.**
- It proves that an unconstrained ripple subtractor severely degrades timing (27.4% drop in Fmax).
- It proves that inferred Yosys subtraction utilizes a much faster adder/subtractor tree mapping in SkyWater SKY130.
- It provides a positive area/power data point (13.6% area reduction, 27.8% power reduction).

---

## 7. Recommended Next Experiment (Experiment 03)

### Proposed Hypothesis
In both the baseline and Exp 01, the datapath computes:
1. `LtComparator_0x422b1f52edd46a85` ($A < B$)
2. `Subtractor_0x422b1f52edd46a85` ($A - B$)

Both operations perform multi-bit comparison/subtraction independently.
**Hypothesis for Experiment 03**: Investigating whether unifying the comparator and subtractor (using the subtractor's borrow/sign bit to determine $A < B$ rather than implementing a separate 16-bit comparator tree) removes redundant logic, cuts datapath input load on registers `a_reg` and `b_reg`, and shortens the critical path into `GcdUnitCtrlRTL`.

