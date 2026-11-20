"""Cycle-accurate Python model verification for AutoSilix Experiment 06 (``gcd.v``).

IMPORTANT SCOPE NOTE
    ``Exp06Model`` below is a hand-written transliteration of ``gcd.v``. It does NOT execute
    the Verilog. A pass here shows that the *model* is correct and that the documented
    cycle-level behaviour is self-consistent; it is not a substitute for the Verilog
    simulation in ``tb_gcd_exp06.v``. Keep the two in sync when the RTL changes.

Independence of the reference
    Expected results come from (a) hand-derived literals in ``DIRECTED_CASES``,
    (b) ``math.gcd`` and (c) a modulo-based Euclid implementation. None of them reuse the
    subtractive algorithm or the split-subtractor equations used by the RTL.
    ``subtract_steps`` (the subtractive step count) is used only for the *latency* check.

Checks performed on every cycle of every scenario (``Bench._monitor``)
    * req_rdy and resp_val are never both high.
    * A pending response (resp_val high, resp_rdy low) stays asserted with unchanged data.
    * After an accepted request, req_rdy and resp_val are both low.
    * After a response handshake, resp_val is low and req_rdy is high.
    * req_rdy does not drop without a request; reset returns the unit to idle.
    * No request is accepted while another is outstanding; every accepted request yields
      exactly one response with the correct data (scoreboard).
    * First resp_val appears exactly 2*n + 2 cycles after the accept cycle, where n is the
      number of subtract/swap steps of the subtractive algorithm.

Usage:
    python verify_exp06.py [--seed N] [--random N] [--skip-exhaustive8] [--json FILE]
"""

import argparse
import json
import math
import random
import sys

STATE_IDLE = 0
STATE_STAGE1 = 1
STATE_STAGE2 = 2
STATE_DONE = 3

CYCLE_CAP = 400_000  # worst case in 16-bit space is 131,075 cycles (gcd(1, 65535))

# (a, b, expected). Literals are hand-derived; they are also cross-checked in main().
# Order and content must match the run_case() calls in tb_gcd_exp06.v.
DIRECTED_CASES = [
    (48, 18, 6),
    (7, 13, 1),
    (16, 16, 16),
    (0, 9, 9),
    (9, 0, 9),
    (0, 0, 0),
    (0, 1, 1),
    (1, 0, 1),
    (100, 100, 100),
    (1, 1, 1),
    (256, 64, 64),
    (1024, 512, 512),
    (0, 32768, 32768),
    (65521, 65519, 1),
    (49999, 50021, 1),
    (65535, 65535, 65535),
    (60000, 45000, 15000),
    (32760, 32736, 24),
    (1, 65535, 1),
    (65535, 1, 1),
    (12, 8, 4),
    (15, 10, 5),
    (21, 14, 7),
    (3, 65535, 3),
    (7, 49, 7),
    (13, 169, 13),
]

BOUNDARY_VALUES = [0, 1, 2, 127, 128, 255, 256, 257, 32767, 32768, 65534, 65535]


def euclid_gcd(a, b):
    """Reference GCD by Euclid's modulo algorithm (independent of the RTL algorithm)."""
    while b:
        a, b = b, a % b
    return a


def subtract_steps(a, b):
    """Number of subtract/swap steps of the subtractive algorithm (latency model only)."""
    steps = 0
    while b:
        if a < b:
            a, b = b, a
        else:
            a -= b
        steps += 1
    return steps


class VerificationError(AssertionError):
    """Raised when any check fails."""


class Exp06Model:
    """Transliteration of gcd.v. Outputs are a function of registered state only."""

    def __init__(self, rng=None):
        self.invariant_checks = 0
        if rng is None:
            self._clear()
        else:
            # Power-up garbage: every register random. Reset must clear it.
            self.state = rng.randrange(4)
            self.a_reg = rng.randrange(65536)
            self.b_reg = rng.randrange(65536)
            self.pipe_diff_lo = rng.randrange(256)
            self.pipe_borrow_mid = rng.randrange(2)
            self.pipe_a_hi = rng.randrange(256)
            self.pipe_b_hi = rng.randrange(256)
            self.pipe_a_lo = rng.randrange(256)
            self.pipe_b_lo = rng.randrange(256)

    def _clear(self):
        self.state = STATE_IDLE
        self.a_reg = 0
        self.b_reg = 0
        self.pipe_diff_lo = 0
        self.pipe_borrow_mid = 0
        self.pipe_a_hi = 0
        self.pipe_b_hi = 0
        self.pipe_a_lo = 0
        self.pipe_b_lo = 0

    def outputs(self):
        """(req_rdy, resp_val, resp_msg) as seen before the next clock edge."""
        return (
            1 if self.state == STATE_IDLE else 0,
            1 if self.state == STATE_DONE else 0,
            self.a_reg,
        )

    def clock(self, req_val, req_msg, resp_rdy, rst):
        """Advance one rising clock edge (synchronous reset, as in gcd.v)."""
        if rst:
            self._clear()
            return

        req_rdy, resp_val, _ = self.outputs()
        is_b_zero = self.b_reg == 0

        # Stage 1 combinational (gcd.v lines 74-75)
        a_lo = self.a_reg & 0xFF
        b_lo = self.b_reg & 0xFF
        diff_lo = (a_lo - b_lo) & 0xFF
        borrow_mid = 1 if a_lo < b_lo else 0

        # Stage 2 combinational (gcd.v lines 86-90): 9-bit unsigned subtraction
        sub_hi_ext = (self.pipe_a_hi - self.pipe_b_hi - self.pipe_borrow_mid) & 0x1FF
        diff_hi = sub_hi_ext & 0xFF
        borrow_final = (sub_hi_ext >> 8) & 1
        sub_diff_full = (diff_hi << 8) | self.pipe_diff_lo

        old_state = self.state
        if old_state == STATE_IDLE:
            if req_val and req_rdy:
                self.a_reg = (req_msg >> 16) & 0xFFFF
                self.b_reg = req_msg & 0xFFFF
                self.state = STATE_STAGE1
        elif old_state == STATE_STAGE1:
            if is_b_zero:
                self.state = STATE_DONE
            else:
                self.pipe_diff_lo = diff_lo
                self.pipe_borrow_mid = borrow_mid
                self.pipe_a_hi = (self.a_reg >> 8) & 0xFF
                self.pipe_b_hi = (self.b_reg >> 8) & 0xFF
                self.pipe_a_lo = a_lo
                self.pipe_b_lo = b_lo
                self.state = STATE_STAGE2
        elif old_state == STATE_STAGE2:
            # Structural invariant used in the README: the pipe copies equal a_reg/b_reg.
            if (
                (self.pipe_a_hi << 8 | self.pipe_a_lo) != self.a_reg
                or (self.pipe_b_hi << 8 | self.pipe_b_lo) != self.b_reg
            ):
                raise VerificationError("pipe_{a,b}_{hi,lo} diverged from a_reg/b_reg in STAGE2")
            self.invariant_checks += 1
            if borrow_final:
                self.a_reg = (self.pipe_b_hi << 8) | self.pipe_b_lo
                self.b_reg = (self.pipe_a_hi << 8) | self.pipe_a_lo
            else:
                self.a_reg = sub_diff_full
                self.b_reg = (self.pipe_b_hi << 8) | self.pipe_b_lo
            self.state = STATE_STAGE1
        else:  # STATE_DONE
            if resp_val and resp_rdy:
                self.state = STATE_IDLE


class Bench:
    """Drives the model one clock at a time and applies the monitor/scoreboard each cycle."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.dut = Exp06Model(random.Random(seed ^ 0xA5A5))
        self.cyc = 0
        self.armed = False  # no checks until the first reset edge has been applied
        self.prev = None
        self.outstanding = False
        self.awaiting_first_resp = False
        self.exp_res = 0
        self.exp_steps = 0
        self.acc_cyc = 0
        self.stats = {
            "accepted": 0,
            "responses": 0,
            "latency_checks": 0,
            "stability_checks": 0,
            "reset_cycles": 0,
            "pipe_invariant_checks": 0,
        }

    def fail(self, message):
        raise VerificationError(f"cycle {self.cyc}: {message}")

    def _monitor(self, outs, req_val, req_msg, resp_rdy, rst):
        req_rdy, resp_val, resp_msg = outs
        if not self.armed:
            self.prev = None
            if rst:
                self.outstanding = False
                self.awaiting_first_resp = False
            return
        if req_rdy and resp_val:
            self.fail("req_rdy and resp_val both high")
        if self.prev is not None:
            p_rst, p_rv, p_rrdy, p_rr, p_rval, p_rmsg = self.prev
            if not p_rst and p_rval and not p_rr:
                if not resp_val or resp_msg != p_rmsg:
                    self.fail("response not stable while resp_rdy low")
                self.stats["stability_checks"] += 1
            if p_rst and (not req_rdy or resp_val):
                self.fail("unit not idle after reset")
            if not p_rst and p_rv and p_rrdy and (req_rdy or resp_val):
                self.fail("after accept expected req_rdy=0 and resp_val=0")
            if not p_rst and p_rval and p_rr and (resp_val or not req_rdy):
                self.fail("after response handshake expected resp_val=0 and req_rdy=1")
            if not p_rst and p_rrdy and not p_rv and not req_rdy:
                self.fail("req_rdy dropped without a request")
        if rst:
            self.outstanding = False
            self.awaiting_first_resp = False
            self.stats["reset_cycles"] += 1
        else:
            if self.awaiting_first_resp and resp_val:
                want = self.acc_cyc + 2 * self.exp_steps + 2
                if self.cyc != want:
                    self.fail(f"latency: first resp_val at {self.cyc}, expected {want}")
                if resp_msg != self.exp_res:
                    self.fail(f"result {resp_msg}, expected {self.exp_res}")
                self.awaiting_first_resp = False
                self.stats["latency_checks"] += 1
            if req_val and req_rdy:
                if self.outstanding:
                    self.fail("request accepted while another is outstanding")
                a = (req_msg >> 16) & 0xFFFF
                b = req_msg & 0xFFFF
                self.exp_res = euclid_gcd(a, b)
                self.exp_steps = subtract_steps(a, b)
                self.outstanding = True
                self.awaiting_first_resp = True
                self.acc_cyc = self.cyc
                self.stats["accepted"] += 1
            if resp_val and resp_rdy:
                if not self.outstanding:
                    self.fail("response handshake with no outstanding request")
                if resp_msg != self.exp_res:
                    self.fail(f"response {resp_msg}, expected {self.exp_res}")
                self.outstanding = False
                self.stats["responses"] += 1
        self.prev = (rst, req_val, req_rdy, resp_rdy, resp_val, resp_msg)

    def cycle(self, req_val=0, req_msg=0, resp_rdy=0, rst=0):
        outs = self.dut.outputs()
        self._monitor(outs, req_val, req_msg, resp_rdy, rst)
        self.dut.clock(req_val, req_msg, resp_rdy, rst)
        if rst:
            self.armed = True
        self.cyc += 1
        self.stats["pipe_invariant_checks"] = self.dut.invariant_checks
        return outs

    def peek(self):
        return self.dut.outputs()

    # ------------------------------------------------------------------ helpers
    def idle(self, count):
        for _ in range(count):
            self.cycle()

    def wait_ready(self):
        waited = 0
        while not self.peek()[0]:
            self.cycle()
            waited += 1
            if waited > CYCLE_CAP:
                self.fail("timeout waiting for req_rdy")

    def wait_resp(self, resp_rdy=0, req_val=0, req_msg=0):
        waited = 0
        while not self.peek()[1]:
            self.cycle(req_val, req_msg, resp_rdy)
            waited += 1
            if waited > CYCLE_CAP:
                self.fail("timeout waiting for resp_val")

    def transaction(self, a, b, start_delay=0, hold=1, early=False, decoy=False):
        """One full request/response. Returns the response data."""
        decoy_msg = self.rng.getrandbits(32)
        self.idle(start_delay)
        self.wait_ready()
        self.cycle(1, (a << 16) | b, 1 if early else 0)
        # While busy: either hold req_val high with a different message, or drive garbage
        # on req_msg with req_val low (the unit must ignore both).
        self.wait_resp(1 if early else 0, 1 if decoy else 0, decoy_msg)
        got = self.peek()[2]
        if not early:
            for _ in range(hold):
                outs = self.cycle(1 if decoy else 0, decoy_msg, 0)
                if not outs[1] or outs[2] != got or outs[0]:
                    self.fail("response not held stable during backpressure")
        self.cycle(1 if decoy else 0, decoy_msg, 1)  # response handshake
        req_rdy, resp_val, _ = self.peek()
        if resp_val or not req_rdy:
            self.fail("unit not idle after response handshake")
        return got

    # ---------------------------------------------------------------- scenarios
    def directed(self):
        for a, b, expected in DIRECTED_CASES:
            got = self.transaction(a, b, 0, 1, False, False)
            if got != expected:
                self.fail(f"gcd({a},{b}) = {got}, expected {expected}")
        return len(DIRECTED_CASES)

    def backpressure(self):
        cases = [(48, 18, 6), (0, 0, 0), (9, 0, 9), (0, 9, 9), (65535, 65535, 65535),
                 (65521, 65519, 1)]
        for a, b, expected in cases:
            got = self.transaction(a, b, 0, 40, False, True)
            if got != expected:
                self.fail(f"backpressure gcd({a},{b}) = {got}, expected {expected}")
        return len(cases)

    def chained(self):
        pairs = [(48, 18, 7, 13), (9, 0, 0, 9), (0, 0, 0, 0), (16, 16, 100, 100),
                 (21, 14, 25, 15), (65535, 1, 1, 65535)]
        for index, (a1, b1, a2, b2) in enumerate(pairs):
            self.wait_ready()
            self.cycle(1, (a1 << 16) | b1, 0)
            msg_b = (a2 << 16) | b2
            self.wait_resp(0, 1, msg_b)  # request B is presented (held) while A is in flight
            if self.peek()[2] != euclid_gcd(a1, b1):
                self.fail("chained: wrong result for first request")
            for _ in range(index * 3):
                self.cycle(1, msg_b, 0)
            before = self.stats["accepted"]
            self.cycle(1, msg_b, 1)  # response handshake while B's req_val is high
            if self.stats["accepted"] != before:
                self.fail("request accepted in the same cycle as the response handshake")
            if not self.peek()[0]:
                self.fail("req_rdy not high the cycle after the response handshake")
            self.cycle(1, msg_b, 0)  # held request B is accepted here
            if self.stats["accepted"] != before + 1:
                self.fail("held request not accepted one cycle after the response")
            self.wait_resp(0)
            if self.peek()[2] != euclid_gcd(a2, b2):
                self.fail("chained: wrong result for second request")
            self.cycle(0, 0, 1)
        return len(pairs)

    def resets(self):
        """Reset at every cycle offset of several transactions, 1- and 2-cycle resets."""
        count = 0
        for a, b in [(48, 18), (7, 13), (16, 16), (9, 0), (0, 9)]:
            span = 2 * subtract_steps(a, b) + 6
            for offset in range(span + 1):
                for width in (1, 2):
                    self.wait_ready()
                    self.cycle(1, (a << 16) | b, 0)
                    for _ in range(offset):
                        if self.peek()[1]:
                            break  # response pending: reset while waiting for resp_rdy
                        self.cycle()
                    for _ in range(width):
                        self.cycle(0, 0, 0, 1)
                    req_rdy, resp_val, _ = self.peek()
                    if not req_rdy or resp_val:
                        self.fail("not idle after mid-transaction reset")
                    self.idle(12)
                    if self.peek()[1]:
                        self.fail("ghost response after reset")
                    if self.transaction(21, 14, 0, 1) != 7:
                        self.fail("fresh transaction after reset returned a wrong result")
                    count += 1
        # Reset coinciding with a request: the request must be dropped.
        self.wait_ready()
        self.cycle(1, (48 << 16) | 18, 0, 1)
        self.idle(20)
        if self.peek()[1]:
            self.fail("request accepted during reset")
        # Reset coinciding with the response handshake.
        self.wait_ready()
        self.cycle(1, (48 << 16) | 18, 0)
        self.wait_resp(0)
        self.cycle(0, 0, 1, 1)
        req_rdy, resp_val, _ = self.peek()
        if not req_rdy or resp_val:
            self.fail("not idle after reset coinciding with resp_rdy")
        if self.transaction(30, 12, 0, 0) != 6:
            self.fail("transaction after reset+resp_rdy returned a wrong result")
        return count

    def randomized(self, count):
        """Random operands (mixed widths) with randomized valid/ready timing and decoys."""
        for _ in range(count):
            a = self.rng.getrandbits(16)
            b = self.rng.getrandbits(16)
            klass = self.rng.randrange(5)
            if klass == 0:
                a &= 0xFF
                b &= 0xFF
            elif klass == 1:
                b &= 0xFF
            elif klass == 2:
                a &= 0xFF
            got = self.transaction(
                a,
                b,
                start_delay=self.rng.randrange(4),
                hold=self.rng.randrange(7),
                early=self.rng.randrange(5) == 0,
                decoy=self.rng.randrange(3) == 0,
            )
            if got != math.gcd(a, b):
                self.fail(f"random gcd({a},{b}) = {got}, expected {math.gcd(a, b)}")
        return count

    def boundary(self):
        count = 0
        for a in BOUNDARY_VALUES:
            for b in BOUNDARY_VALUES:
                got = self.transaction(a, b, 0, 0, True)
                if got != math.gcd(a, b):
                    self.fail(f"boundary gcd({a},{b}) = {got}, expected {math.gcd(a, b)}")
                count += 1
        return count

    def exhaustive8(self):
        """Every (a, b) with both operands in [0, 255]."""
        count = 0
        for a in range(256):
            for b in range(256):
                got = self.transaction(a, b, 0, 0, True)
                if got != math.gcd(a, b):
                    self.fail(f"exhaustive8 gcd({a},{b}) = {got}, expected {math.gcd(a, b)}")
                count += 1
        return count


def run_all(seed=42, random_vectors=10000, exhaustive8=True):
    """Run every scenario and return a summary dictionary (raises on the first failure)."""
    for a, b, expected in DIRECTED_CASES:
        if not (expected == math.gcd(a, b) == euclid_gcd(a, b)):
            raise VerificationError(f"literal expected value wrong for gcd({a},{b})")
    bench = Bench(seed)
    for _ in range(3):
        bench.cycle(0, 0, 0, 1)  # power-up reset (state was randomized)
    summary = {"seed": seed, "model": "python transliteration of gcd.v (not the RTL)"}
    summary["directed_cases"] = bench.directed()
    summary["backpressure_cases"] = bench.backpressure()
    summary["chained_pairs"] = bench.chained()
    summary["reset_scenarios"] = bench.resets()
    summary["boundary_cases"] = bench.boundary()
    summary["random_vectors"] = bench.randomized(random_vectors)
    summary["exhaustive_8bit_pairs"] = bench.exhaustive8() if exhaustive8 else 0
    summary["monitor"] = dict(bench.stats)
    summary["clock_cycles"] = bench.cyc
    summary["status"] = "PASS"
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--random", type=int, default=10000, dest="random_vectors")
    parser.add_argument("--skip-exhaustive8", action="store_true")
    parser.add_argument("--json", metavar="FILE", help="write the summary as JSON")
    args = parser.parse_args(argv)

    print("=== AutoSilix Exp06 Python-model verification (model of gcd.v, not the RTL) ===")
    try:
        summary = run_all(args.seed, args.random_vectors, not args.skip_exhaustive8)
    except VerificationError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(f"[PASS] directed cases:           {summary['directed_cases']}")
    print(f"[PASS] backpressure cases:       {summary['backpressure_cases']}")
    print(f"[PASS] chained request pairs:    {summary['chained_pairs']}")
    print(f"[PASS] reset scenarios:          {summary['reset_scenarios']}")
    print(f"[PASS] boundary cross product:   {summary['boundary_cases']}")
    print(f"[PASS] randomized vectors:       {summary['random_vectors']}")
    print(f"[PASS] exhaustive 8-bit pairs:   {summary['exhaustive_8bit_pairs']}")
    mon = summary["monitor"]
    print(
        f"       monitor: {mon['accepted']} accepted, {mon['responses']} responses, "
        f"{mon['latency_checks']} latency checks, {mon['stability_checks']} stability checks, "
        f"{mon['reset_cycles']} reset cycles, {mon['pipe_invariant_checks']} pipe-copy checks"
    )
    print(f"       clock cycles simulated: {summary['clock_cycles']}")
    print("=== ALL EXP06 MODEL CHECKS PASSED ===")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
