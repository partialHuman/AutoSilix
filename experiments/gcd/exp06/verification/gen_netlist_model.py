#!/usr/bin/env python3
"""Generate a C cycle model (netlist_model.h) from a flat Yosys/SKY130 gate-level netlist.

Only the cell functions used by the Exp06 synthesized netlist are implemented; an unknown
cell type aborts generation. Cell functions are written from the SKY130 cell naming/pin
conventions; a wrong function shows up as a GCD mismatch in gate_level_tb.c (it cannot make
the test pass spuriously). Combinational cells are topologically sorted; loops abort.

Usage: python3 gen_netlist_model.py <netlist.v> <netlist_model.h>
"""

import re
import sys

FUNCS = {
    "a211o": ("X", "(A1&A2)|B1|C1"),
    "a211oi": ("Y", "~((A1&A2)|B1|C1)"),
    "a21boi": ("Y", "~((A1&A2)|~B1_N)"),
    "a21o": ("X", "(A1&A2)|B1"),
    "a21oi": ("Y", "~((A1&A2)|B1)"),
    "a221o": ("X", "(A1&A2)|(B1&B2)|C1"),
    "a221oi": ("Y", "~((A1&A2)|(B1&B2)|C1)"),
    "a22oi": ("Y", "~((A1&A2)|(B1&B2))"),
    "a31oi": ("Y", "~((A1&A2&A3)|B1)"),
    "a32oi": ("Y", "~((A1&A2&A3)|(B1&B2))"),
    "and2": ("X", "A&B"),
    "and3": ("X", "A&B&C"),
    "and4": ("X", "A&B&C&D"),
    "clkinv": ("Y", "~A"),
    "maj3": ("X", "(A&B)|(A&C)|(B&C)"),
    "mux2i": ("Y", "~((S&A1)|(~S&A0))"),
    "nand2": ("Y", "~(A&B)"),
    "nand2b": ("Y", "~(~A_N&B)"),
    "nand3": ("Y", "~(A&B&C)"),
    "nand4": ("Y", "~(A&B&C&D)"),
    "nand4b": ("Y", "~(~A_N&B&C&D)"),
    "nor2": ("Y", "~(A|B)"),
    "nor2b": ("Y", "~(A|~B_N)"),
    "nor3": ("Y", "~(A|B|C)"),
    "nor3b": ("Y", "~(A|B|~C_N)"),
    "nor4": ("Y", "~(A|B|C|D)"),
    "nor4bb": ("Y", "~(A|B|~C_N|~D_N)"),
    "o2111ai": ("Y", "~((A1|A2)&B1&C1&D1)"),
    "o211ai": ("Y", "~((A1|A2)&B1&C1)"),
    "o21a": ("X", "(A1|A2)&B1"),
    "o21ai": ("Y", "~((A1|A2)&B1)"),
    "o21bai": ("Y", "~((A1|A2)&~B1_N)"),
    "o221a": ("X", "(A1|A2)&(B1|B2)&C1"),
    "o221ai": ("Y", "~((A1|A2)&(B1|B2)&C1)"),
    "o22ai": ("Y", "~((A1|A2)&(B1|B2))"),
    "o311a": ("X", "(A1|A2|A3)&B1&C1"),
    "o31ai": ("Y", "~((A1|A2|A3)&B1)"),
    "o41ai": ("Y", "~((A1|A2|A3|A4)&B1)"),
    "or3": ("X", "A|B|C"),
    "or3b": ("X", "A|B|~C_N"),
    "or4": ("X", "A|B|C|D"),
    "xnor2": ("Y", "~(A^B)"),
    "xor2": ("X", "A^B"),
}

CELL_RE = re.compile(r"sky130_fd_sc_hd__(\w+?)_\d+\s+(\S+)\s*\((.*?)\);", re.S)
PIN_RE = re.compile(r"\.(\w+)\((.*?)\)", re.S)


def generate(netlist, out):
    text = open(netlist, encoding="utf-8").read()
    nets = {}

    def net_id(name):
        return nets.setdefault(name.strip(), len(nets))

    flops = []
    comb = []
    for cell_type, _name, body in CELL_RE.findall(text):
        pins = {pin: net_id(value) for pin, value in PIN_RE.findall(body)}
        if cell_type == "dfxtp":
            flops.append((pins["D"], pins["Q"]))
        elif cell_type in FUNCS:
            out_pin, expr = FUNCS[cell_type]
            inputs = {k: v for k, v in pins.items() if k != out_pin}
            comb.append((pins[out_pin], expr, inputs))
        else:
            sys.exit("unsupported cell type: " + cell_type)

    primary_in = {f"req_msg[{i}]" for i in range(32)} | {"req_val", "resp_rdy", "reset", "clk"}
    for name in primary_in:
        net_id(name)
    for name in ["req_rdy", "resp_val"] + [f"resp_msg[{i}]" for i in range(16)]:
        net_id(name)

    driven = {o for o, _, _ in comb} | {q for _, q in flops} | {nets[p] for p in primary_in}
    if len(driven) != len(comb) + len(flops) + len(primary_in):
        sys.exit("multiple drivers detected")
    undriven = set(nets.values()) - driven
    if undriven:
        sys.exit(f"undriven nets: {sorted(undriven)}")

    ready = {nets[p] for p in primary_in} | {q for _, q in flops}
    order = []
    pending = list(comb)
    while pending:
        now = [c for c in pending if all(i in ready for i in c[2].values())]
        if not now:
            sys.exit("combinational loop or unresolved dependency")
        for cell in now:
            ready.add(cell[0])
        order += now
        pending = [c for c in pending if c not in now]

    with open(out, "w", encoding="utf-8") as handle:
        handle.write(
            f"/* generated from {netlist}: {len(comb)} comb cells, {len(flops)} flops, "
            f"{len(nets)} nets */\n"
        )
        handle.write(f"#define NNETS {len(nets)}\n#define NFLOPS {len(flops)}\n")
        for key in ["req_val", "resp_rdy", "reset", "req_rdy", "resp_val"]:
            handle.write(f"#define N_{key.upper()} {nets[key]}\n")
        req = ",".join(str(nets[f"req_msg[{i}]"]) for i in range(32))
        resp = ",".join(str(nets[f"resp_msg[{i}]"]) for i in range(16))
        handle.write(f"static const int N_REQ_MSG[32]={{{req}}};\n")
        handle.write(f"static const int N_RESP_MSG[16]={{{resp}}};\n")
        handle.write("static const int FLOP_D[NFLOPS]={" + ",".join(str(d) for d, _ in flops) + "};\n")
        handle.write("static const int FLOP_Q[NFLOPS]={" + ",".join(str(q) for _, q in flops) + "};\n")
        handle.write("static inline void eval_comb(unsigned char *n){\n")
        for out_net, expr, pins in order:
            for pin in sorted(pins, key=len, reverse=True):
                expr = re.sub(r"\b" + pin + r"\b", f"n[{pins[pin]}]", expr)
            handle.write(f"  n[{out_net}]=({expr})&1;\n")
        handle.write("}\n")
    print(f"{len(comb)} comb + {len(flops)} flops; topological order OK; wrote {out}")


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    generate(argv[1], argv[2])


if __name__ == "__main__":
    main(sys.argv)
