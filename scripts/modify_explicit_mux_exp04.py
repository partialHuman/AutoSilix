"""
Modify experiments/gcd/exp04/gcd.v:
Replace `out = in_[sel];` in Mux_0x683fa1a418b072c9 with explicit AND/OR selection logic.
Leave Mux_0xdd6473406d1a99a (2-input mux) and all other modules untouched.
"""
from pathlib import Path

gcd_file = Path("experiments/gcd/exp04/gcd.v")
content = gcd_file.read_text(encoding="utf-8")

target = """module Mux_0x683fa1a418b072c9
(
  input  wire [   0:0] clk,
  input  wire [  15:0] in_$000,
  input  wire [  15:0] in_$001,
  input  wire [  15:0] in_$002,
  output reg  [  15:0] out,
  input  wire [   0:0] reset,
  input  wire [   1:0] sel
);

  // localparam declarations
  localparam nports = 3;


  // array declarations
  wire   [  15:0] in_[0:2];
  assign in_[  0] = in_$000;
  assign in_[  1] = in_$001;
  assign in_[  2] = in_$002;

  // PYMTL SOURCE:
  //
  // @s.combinational
  // def comb_logic():
  //       assert s.sel < nports
  //       s.out.v = s.in_[ s.sel ]

  // logic for comb_logic()
  always @ (*) begin
    out = in_[sel];
  end


endmodule // Mux_0x683fa1a418b072c9"""

replacement = """module Mux_0x683fa1a418b072c9
(
  input  wire [   0:0] clk,
  input  wire [  15:0] in_$000,
  input  wire [  15:0] in_$001,
  input  wire [  15:0] in_$002,
  output reg  [  15:0] out,
  input  wire [   0:0] reset,
  input  wire [   1:0] sel
);

  // localparam declarations
  localparam nports = 3;


  // array declarations
  wire   [  15:0] in_[0:2];
  assign in_[  0] = in_$000;
  assign in_[  1] = in_$001;
  assign in_[  2] = in_$002;

  // PYMTL SOURCE:
  //
  // @s.combinational
  // def comb_logic():
  //       assert s.sel < nports
  //       s.out.v = s.in_[ s.sel ]

  // logic for comb_logic()
  always @ (*) begin
    out = ({16{sel == 2'd0}} & in_$000)
        | ({16{sel == 2'd1}} & in_$001)
        | ({16{sel == 2'd2}} & in_$002);
  end


endmodule // Mux_0x683fa1a418b072c9"""

assert target in content, "Target block not found in exp04/gcd.v"
new_content = content.replace(target, replacement, 1)
assert target not in new_content, "Replacement failed"
assert replacement in new_content, "Replacement verification failed"

gcd_file.write_text(new_content, encoding="utf-8")
print("Successfully modified experiments/gcd/exp04/gcd.v")

