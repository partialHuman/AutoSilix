# 8-Bit ALU Accumulator

## Overview
An 8-bit Arithmetic Logic Unit with an internal accumulator register, zero flag, carry flag, and overflow flag.

## Specifications
- **Data Width**: 8-bit
- **Clock**: Synchronous on `clk`
- **Reset**: Asynchronous active-low `rst_n`
- **Enable**: `enable` gating register updates
- **Opcodes**:
  - `3'b000`: NOP (hold state)
  - `3'b001`: LOAD (load accumulator with `operand_b`)
  - `3'b010`: ADD (accumulate sum)
  - `3'b011`: SUB (accumulate difference)
  - `3'b100`: AND (bitwise AND)
  - `3'b101`: OR (bitwise OR)
  - `3'b110`: XOR (bitwise XOR)
  - `3'b111`: NOT (bitwise inversion)
