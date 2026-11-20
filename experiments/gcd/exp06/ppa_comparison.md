# PPA Comparison: GCD Baseline vs. Exp 01 through Exp 06

> **Status of Exp 06: NOT timing-closed.** The 1.10 ns target has **not** been met.
> The only physical results that exist for Exp 06 are **detailed-placement** results
> (ideal clock, no CTS, no routing). No routed area, power or timing exists.
> Nothing in this document should be read as a routed or signed-off result.

Terminology used throughout:

| Label | Meaning |
|:---|:---|
| **Analytical estimate** | Pre-implementation hand calculation. Never measured. |
| **Synthesis measurement** | Yosys netlist statistics (ORFS `1_2_yosys`). |
| **Placement measurement** | OpenROAD report after detailed placement (ORFS `3_5_place_dp`). |
| **Routed measurement** | Post-route/finish report. **None exists for Exp 06.** |

---

## 1. Executive Summary

Experiment 06 implements an **8-bit split, two-stage arithmetic pipeline** hoping to shorten
the single-cycle subtract-and-select path that limits the Baseline through Exp 05 designs.

What was measured (detailed placement, 1.10 ns constraint):

1. **Setup timing is far from closed**: WNS -1.2638 ns, TNS -67.6511 ns, 84 violating
   endpoints, minimum period 2.36 ns (423.05 MHz). Hold: 0 violations.
2. **The critical path is the high-byte borrow chain feeding the write-back select**:
   `pipe_b_hi[5]` to `b_reg[7]`, 2.55 ns arrival against a 1.29 ns required time. By structure
   and fanout (the report names internal nets only as `_NNN_`), a fanout-14 signal, then a
   fanout-9 buffer, drives the `a_reg`/`b_reg` write-back muxes; this is consistent with
   `borrow_final` acting as the swap/subtract select.
3. **A smaller `req_rdy` output violation exists**: -0.16 ns (1.33 ns arrival, 1.17 ns
   required). The path is flop, a buffer driving 11 loads (0.20 ns), then the 0.48 ns
   `clkdlybuf4s50_1` output port buffer that ORFS inserts on all 18 outputs.
   The worst reported output path is `req_rdy`. The project owner reports that `resp_msg`
   meets timing, but the provided reports list only the worst path per group, so that is not
   independently verifiable here (it is at least -0.16 ns).
4. **The original analytical estimates were wrong.** They predicted ~650 MHz, a ~-0.40 ns
   stage-2 WNS and a met output path. See Appendix A for the preserved (superseded) estimates.
5. **Per-iteration speed is worse than the single-cycle designs on the measured numbers.**
   Exp 06 needs 2 cycles per subtract/swap step. At the measured 2.36 ns minimum period that
   is 4.73 ns per step, against 2.50 ns for Exp 05 (1 cycle at 400.75 MHz). See the caveats
   in section 2 before drawing conclusions: the two numbers come from different flow stages.

Verification status is summarised in section 6.

---

## 2. Seven-Way PPA Comparison Table

Baseline to Exp 05 columns are the historical **finish-stage** (`6_report`) values and are
unchanged. The Exp 06 column is **detailed-placement** data. **The columns are not like-for-like.**

| Metric | Baseline | Exp 01 | Exp 02 | Exp 03 | Exp 04 | Exp 05 | Exp 06 (**measured, placement stage**) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Architecture** | Single-Cycle | Explicit Mux | Ripple Sub | 17b Sub+Comp | 17b Sub+Mux | Native 16b Sub | **2-Stage 8b Split Pipeline** |
| **Flow stage of numbers** | finish | finish | finish | finish | finish | finish | **detailed placement** |
| **Setup WNS (ns)** | -1.3954 | **-1.3625** | -2.3619 | -1.4911 | -1.5115 | -1.3954 | **-1.2638** |
| **Output WNS (ns)** | -1.2600 | -1.2300 | -2.1500 | -1.3400 | -1.3600 | -1.2600 | **-0.16 (`req_rdy`, worst output path)** |
| **Setup TNS (ns)** | -62.6899 | **-61.6748** | -72.5953 | -64.6083 | -67.3086 | -62.6899 | **-67.6511** |
| **Min period (ns)** | 2.495 | 2.463 | 3.439 | 2.591 | 2.612 | 2.495 | **2.36** |
| **Effective Fmax (MHz)** | 400.75 | 406.09 | 290.77 | 385.94 | 382.92 | 400.75 | **423.05** |
| **Setup Violations** | 63 | 65 | 81 | 58 | 84 | 63 | **84** |
| **Hold Violations** | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| **Std-Cell / Instance Area (µm²)** | 5,236.27 | 4,942.24 | 4,523.09 | 4,748.30 | 4,755.81 | 5,236.27 | **6,073.32** (includes tap cells and 53 port buffers) |
| **Estimated Power (mW)** | 9.292 | 8.404 | 6.706 | 8.308 | 8.405 | 9.292 | **5.966** (placement estimate, ideal clock, no clock-tree power) |
| **Total Flop Count** | 34 | 34 | 34 | 34 | 34 | 34 | **77 synthesized** (75 declared; FSM re-encoded one-hot, +2) |
| **Cycles / Iteration** | 1 | 1 | 1 | 1 | 1 | 1 | **2** |
| **Time per subtract/swap step (ns)** | 2.50 | 2.46 | 3.44 | 2.59 | 2.61 | 2.50 | **4.73** (2 x 2.36) |
| **Routed result** | yes | yes | yes | yes | yes | yes | **none** |

Comparability warnings (also recorded in `ppa_results.json`):

- **Different flow stages.** Finish-stage numbers include CTS and route parasitics; the Exp 06
  numbers do not. Routed Exp 06 timing would normally be no better than placement timing.
  Placement-stage numbers for the earlier experiments are not in the repository, so no
  like-for-like comparison is possible yet.
- **Different floorplans.** Exp 06: die 11,299.7 µm², core 10,416.2 µm², 58.3% utilization.
  Exp 05: die 6,404.0 µm², core 5,885.64 µm², 88.97% utilization. Area and utilization
  therefore cannot be compared directly.
- **Power** is a placement-stage estimate with an ideal clock (clock power is zero), so it is
  not comparable with finish-stage power.
- **Flop count.** The README/JSON previously said 75. The RTL declares 75 flops (2 state + 32
  operand + 41 pipeline); the synthesized netlist has 77 because Yosys re-encoded the 2-bit
  FSM as 4 one-hot flops.
- **Repair buffers.** Exp 05's finish-stage area includes 1,741.67 µm² of timing-repair
  buffers (from its `ppa_results.json`). Exp 06's placement-stage area contains none of that,
  so a routed Exp 06 area would be expected to be larger than 6,073 µm², not smaller.
- **WNS vs. data-path delay.** The Exp 06 critical-path *arrival* time (2.55 ns, placement) is
  essentially the same as the Baseline's (2.54 ns, finish; Exp 05 reports the same WNS). The
  better slack (-1.26 vs -1.395) comes mainly from a larger required time (1.29 vs 1.15 ns):
  the Exp 06 endpoint is a plain `dfxtp` flop (about 0.10 ns setup), whereas an earlier
  experiment's finish report shows an enable-flop `edfxtp_1` endpoint with 0.24 ns setup.
  On this evidence the 8-bit split did **not** shorten the critical data path. A stage-matched
  comparison is needed before attributing any gain to the pipeline.

---

## 3. Measured Critical Paths

### Exp 06, detailed placement (from `3_detailed_place.rpt`; clock latency 0.29 ns ideal)

```
Worst reg2reg setup path (core_clock): slack -1.26 ns (VIOLATED)
  pipe_b_hi[5]  dfxtp_2   clk->Q   0.37 ns  (fanout 4)
  xor2_2                           0.23 ns  (fanout 5)
  nor3b_1                          0.09 ns
  a211oi_1                         0.32 ns
  a221o_1                          0.27 ns
  a21o_2                           0.40 ns  (fanout 14)
  buf_4 (place173)                 0.26 ns  (fanout 9)
  nand2_1                          0.07 ns
  a221oi_1                         0.26 ns
  b_reg[7]/D    arrival 2.55 ns, required 1.29 ns

Worst output path (vclk_core_clock): slack -0.16 ns (VIOLATED)
  state[0]  dfxtp_4  clk->Q        0.36 ns  (fanout 5)
  buf_4 (place244)                 0.20 ns  (fanout 11)
  clkdlybuf4s50_1 (output36)       0.48 ns  (port buffer)
  req_rdy       arrival 1.33 ns, required 1.17 ns
```

The output budget is 1.10 ns (period) - 0.22 ns (output delay) = 0.88 ns after the clock edge.
Clock-to-Q (0.36 ns) plus the 0.48 ns port buffer already uses 0.84 ns, so any extra loading
on the driving flop violates the output path. ORFS inserted all 35 input and 18 output port
buffers as `clkdlybuf4s50_1` (RSZ-0027/0028 in `3_3_place_gp.log`).

### Baseline, single-cycle (historical, finish stage; unchanged)

```
Baseline Critical Path (Single-Cycle):
dpath.b_reg/CLK (0.31 ns)
  └── Q clk-to-q (0.42 ns)
       └── 16-bit Kogge-Stone Subtractor (1.10 ns)
            └── Sizing buffers (0.24 ns)
                 └── A-Mux (0.21 ns)
                      └── a_reg setup (0.26 ns)
Arrival: 2.54 ns | Required: 1.15 ns | Slack: -1.3954 ns
```

---

## 4. Latency vs. Throughput (measured basis)

| Metric | Single-cycle (Exp 05, finish stage) | Exp 06 (placement stage) | Impact |
|---|---|---|---|
| Min clock period | 2.495 ns (400.75 MHz) | 2.36 ns (423.05 MHz) | 5.6% shorter period |
| Cycles per subtract/swap step | 1 | 2 | 2x |
| Time per step | 2.50 ns | 4.73 ns | **about 1.9x slower per iteration** |
| Latency, request to `resp_val` | not characterised here | 2n+2 edges (n = subtract/swap steps; checked in model and gate-level simulation) | |
| Worst-case latency (`gcd(1,65535)`, n=65,537) | n/a | 131,076 edges | |

The 5.6% frequency gain does not compensate the doubled cycle count. If the placement-stage
period were representative, Exp 06 would be slower than Exp 05 per GCD result. A routed run is
needed to confirm, and may be worse for Exp 06.

---

## 5. Engineering Conclusions

1. **The split-pipeline hypothesis is not supported by the measured data so far.** The critical
   path moved to the high-byte borrow chain plus the write-back select, and its arrival time
   (2.55 ns) did not decrease versus the single-cycle design (2.54 ns).
2. **Output decoupling alone did not close the output path.** Driving `resp_msg` from `a_reg`
   removes the subtractor from that path, but the `req_rdy` path is still limited by loading on
   the FSM state flop and by the 0.48 ns port buffer. This is a flow/loading effect, not
   something the 2-stage arithmetic split addresses.
3. **Cost.** 77 flops against 34, plus the doubled iteration count, for no demonstrated
   throughput gain.
4. **Open, unmeasured ideas** (none applied, none validated; each needs approval and a run):
   - 32 of the 41 pipeline flops (`pipe_{a,b}_{hi,lo}`) are functionally redundant copies of
     `a_reg`/`b_reg` bytes. Removing them saves about 640 µm² of flop area (32 x 20.02 µm²,
     before their enable/reset gating) but its timing effect is unknown, since they currently
     isolate the stage-2 start flops from `a_reg`/`b_reg` fanout.
   - A dedicated lightly loaded flop for `req_rdy` could address the -0.16 ns output path
     without changing cycle behaviour.
   - Registering `borrow_final` would shorten the critical path but adds a cycle per step
     (architecture change).
5. **Verification** is described in section 6; it does not depend on any timing result.

---

## 6. Verification Status (functional, not physical)

| Layer | Scope | Result |
|:---|:---|:---|
| Verilog RTL simulation, revised `tb_gcd_exp06.v` | 26 directed, 6 backpressure, 6 chained, reset at every offset, 144 boundary, 1000 random with random handshake timing; continuous protocol monitor | **NOT YET RUN** (no simulator in the review environment) |
| Verilog RTL simulation, previous testbench | 24 directed + 1000 random + reset recovery | Reported passed by the project owner (older, weaker testbench) |
| Python cycle-accurate model (`verify_exp06.py`, seed 42) | 26 directed, 6 backpressure, 6 chained, 162 reset scenarios, 144 boundary, 10,000 random, 65,536 exhaustive 8-bit pairs; 75,887 responses and latency checks | PASS (model of the RTL, not the RTL) |
| Exhaustive split-subtractor check (C) | all 2^32 operand pairs | PASS, 0 mismatches |
| Post-synthesis netlist simulation (C model of `1_2_yosys.v`) | 600,337 transactions, 600,337 latency checks | PASS, 0 mismatches |
| `tests/rtl/tb_gcd_extended.v` | shared testbench | Not applicable to Exp 06 as written (5,000-cycle per-case cap) |

---

## Appendix A. Historical Analytical Estimates (SUPERSEDED, never measured)

These pre-implementation numbers are preserved only for history. They disagree with the
measured results above and **must not be quoted as results**.

| Metric | Historical analytical estimate | Measured (placement) |
|:---|:---:|:---:|
| Setup WNS | ~ -0.40 ns (Stage 2) | -1.2638 ns |
| Output WNS | +0.35 ns (MET) | -0.16 ns (`req_rdy`) |
| Setup TNS | ~ -12.5 ns | -67.6511 ns |
| Effective Fmax | ~ 645 - 670 MHz | 423.05 MHz |
| Setup violations | ~ 18 | 84 |
| Std-cell area | ~ 5,350 - 5,500 µm² | 6,073.32 µm² (placement, different floorplan) |
| Estimated power | ~ 9.5 - 10.2 mW | 5.966 mW (placement, ideal clock) |
| Flop count | 75 (+41 pipeline) | 77 synthesized |

Historical estimated path breakdowns (assumed delays, not measurements):

```
Exp 06 Stage 1 (estimate): clk-to-q 0.42 + 8-bit subtractor 0.49 + setup 0.20 -> slack ~ -0.01 ns
Exp 06 Stage 2 (estimate): clk-to-q 0.36 + 8-bit sub w/ borrow 0.45 + 2:1 mux 0.18 + wire 0.25
                           + setup 0.26 -> slack ~ -0.40 ns
Exp 06 Output  (estimate): clk-to-q 0.42 + pad buffer 0.40 + output delay 0.22 -> slack ~ +0.35 ns
```

The estimates assumed a 0.40 ns output buffer and no loading on the state flop, an 8-bit
carry chain of ~0.45 ns, and a 2-input write-back mux. The measured placement showed a 0.48 ns
output buffer plus a 0.20 ns fanout buffer, and a high-byte borrow chain with a fanout-14/-9
select network; the end of that select network is reached about 1.93 ns after the clock edge (including clock-to-Q).
