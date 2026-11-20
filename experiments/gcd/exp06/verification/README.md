# Exp06 optional verification tools (new; need approval before adoption)

These tools were added during the Exp06 review because no Verilog simulator was available.
They need only `gcc` and Python 3. None of them replaces simulating `gcd.v` itself with
`tb_gcd_exp06.v`.

| File | Purpose |
|---|---|
| `exhaustive_split_sub.c` | Checks the split-subtractor equations of `gcd.v` (transcribed with Verilog widths) against plain integer arithmetic for all 2^32 `(a, b)` pairs. About 10 s. |
| `gen_netlist_model.py` | Converts the flat Yosys/SKY130 netlist `1_2_yosys.v` into a C cycle model (`netlist_model.h`). Aborts on an unknown cell type, a multiply-driven or undriven net, or a combinational loop. |
| `gate_level_tb.c` | Cycle-accurate testbench for that model: scoreboard with an independent Euclid reference, protocol monitor, 2n+2 latency check, backpressure, held `req_val`, reset at every cycle offset, randomized timing, dense borrow-in sweep. About 30 s; `QUICK=1` skips the 590k-transaction sweep. |

```bash
gcc -O2 -o /tmp/exhaustive_split_sub exhaustive_split_sub.c && /tmp/exhaustive_split_sub
python3 gen_netlist_model.py <orfs results>/1_2_yosys.v netlist_model.h
gcc -O2 -Wall -o /tmp/gate_level_tb gate_level_tb.c && /tmp/gate_level_tb
```

Limitations:

- The cell functions in `gen_netlist_model.py` were written from SKY130 naming conventions.
  An error there would show up as a GCD mismatch, not a false pass; 60 of 60 single-gate
  output inversions were detected by the harness.
- The model is functional only. It carries no timing and says nothing about placement.
- `netlist_model.h` is generated and should not be committed.
