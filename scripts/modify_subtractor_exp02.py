import sys

path = "experiments/gcd/exp02/gcd.v"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """  // PYMTL SOURCE:
  //
  // @s.combinational
  // def comb_logic():
  //       s.out.value = s.in0 - s.in1

  // logic for comb_logic()
  always @ (*) begin
    out = (in0-in1);
  end"""

replacement = """  wire [16:0] borrow;
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
  end"""

normalized_content = content.replace("\r\n", "\n")
if target not in normalized_content:
    print("ERROR: Target text not found in file", file=sys.stderr)
    sys.exit(1)

count = normalized_content.count(target)
if count != 1:
    print(f"ERROR: Target found {count} times (expected 1)", file=sys.stderr)
    sys.exit(1)

new_content = normalized_content.replace(target, replacement, 1)

# Check line endings of original content
if "\r\n" in content:
    new_content = new_content.replace("\n", "\r\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("SUCCESS: Subtractor replaced cleanly in exp02/gcd.v")

