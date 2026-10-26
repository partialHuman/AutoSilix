import sys

path = "experiments/gcd/exp03/gcd.v"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

normalized = content.replace("\r\n", "\n")

# 1. Target: a_lt_b instance in dpath
target_altb = """  // a_lt_b temporaries
  wire   [   0:0] a_lt_b$reset;
  wire   [   0:0] a_lt_b$clk;
  wire   [  15:0] a_lt_b$in0;
  wire   [  15:0] a_lt_b$in1;
  wire   [   0:0] a_lt_b$out;

  LtComparator_0x422b1f52edd46a85 a_lt_b
  (
    .reset ( a_lt_b$reset ),
    .clk   ( a_lt_b$clk ),
    .in0   ( a_lt_b$in0 ),
    .in1   ( a_lt_b$in1 ),
    .out   ( a_lt_b$out )
  );"""

# Replace with comment indicating removal in Exp03
repl_altb = """  // a_lt_b removed in Exp03 (unified with subtractor)"""

# 2. Target: sub temporaries & instance in dpath
target_sub = """  // sub temporaries
  wire   [   0:0] sub$reset;
  wire   [   0:0] sub$clk;
  wire   [  15:0] sub$in0;
  wire   [  15:0] sub$in1;
  wire   [  15:0] sub$out;

  Subtractor_0x422b1f52edd46a85 sub
  (
    .reset ( sub$reset ),
    .clk   ( sub$clk ),
    .in0   ( sub$in0 ),
    .in1   ( sub$in1 ),
    .out   ( sub$out )
  );"""

repl_sub = """  // sub temporaries (unified 17-bit subtractor + comparator)
  wire   [   0:0] sub$reset;
  wire   [   0:0] sub$clk;
  wire   [  15:0] sub$in0;
  wire   [  15:0] sub$in1;
  wire   [  15:0] sub$out;
  wire   [   0:0] sub$lt;

  Subtractor_0x422b1f52edd46a85 sub
  (
    .reset ( sub$reset ),
    .clk   ( sub$clk ),
    .in0   ( sub$in0 ),
    .in1   ( sub$in1 ),
    .out   ( sub$out ),
    .lt    ( sub$lt )
  );"""

# 3. Target: signal connections in dpath
target_conns = """  // signal connections
  assign a_lt_b$clk    = clk;
  assign a_lt_b$in0    = a_reg$out;
  assign a_lt_b$in1    = b_reg$out;
  assign a_lt_b$reset  = reset;"""

repl_conns = """  // signal connections"""

target_is_altb = """  assign is_a_lt_b     = a_lt_b$out;"""
repl_is_altb   = """  assign is_a_lt_b     = sub$lt;"""

# 4. Target: Subtractor module definition
target_sub_mod = """module Subtractor_0x422b1f52edd46a85
(
  input  wire [   0:0] clk,
  input  wire [  15:0] in0,
  input  wire [  15:0] in1,
  output reg  [  15:0] out,
  input  wire [   0:0] reset
);



  // PYMTL SOURCE:
  //
  // @s.combinational
  // def comb_logic():
  //       s.out.value = s.in0 - s.in1

  // logic for comb_logic()
  always @ (*) begin
    out = (in0-in1);
  end


endmodule // Subtractor_0x422b1f52edd46a85"""

repl_sub_mod = """module Subtractor_0x422b1f52edd46a85
(
  input  wire [   0:0] clk,
  input  wire [  15:0] in0,
  input  wire [  15:0] in1,
  output reg  [  15:0] out,
  output reg  [   0:0] lt,
  input  wire [   0:0] reset
);

  reg [16:0] diff_ext;

  // 17-bit zero-extended unsigned subtraction:
  // diff_ext[15:0] provides the 16-bit difference (out)
  // diff_ext[16]   provides the borrow-out indicating in0 < in1 (lt)
  always @ (*) begin
    diff_ext = {1'b0, in0} - {1'b0, in1};
    out = diff_ext[15:0];
    lt  = diff_ext[16];
  end

endmodule // Subtractor_0x422b1f52edd46a85"""

# Verify all targets exist
for name, t in [("altb", target_altb), ("sub", target_sub), ("conns", target_conns),
                ("is_altb", target_is_altb), ("sub_mod", target_sub_mod)]:
    if t not in normalized:
        print(f"ERROR: Target '{name}' not found in file", file=sys.stderr)
        sys.exit(1)

new_content = normalized.replace(target_altb, repl_altb, 1)
new_content = new_content.replace(target_sub, repl_sub, 1)
new_content = new_content.replace(target_conns, repl_conns, 1)
new_content = new_content.replace(target_is_altb, repl_is_altb, 1)
new_content = new_content.replace(target_sub_mod, repl_sub_mod, 1)

if "\r\n" in content:
    new_content = new_content.replace("\n", "\r\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("SUCCESS: Exp03 unified comparator-subtractor applied cleanly.")

