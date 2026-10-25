# Sequence Detector (1011 Overlapping)

## Overview
A synthesizable sequential digital design that detects the 4-bit sequence `1011` on a serial input line `data_in`.

## Specifications
- **Target Pattern**: `1011`
- **Clock**: Positive edge-triggered (`clk`)
- **Reset**: Asynchronous active-low (`rst_n`)
- **Overlapping Mode**: Supported. When `1011` is detected, the last `1` serves as the first `1` of the next candidate sequence (e.g. `1011011` produces two pulses).
- **Output**: `seq_detected` pulses HIGH for 1 clock cycle upon receiving the 4th bit.

## State Transition Table
| Current State | Input `data_in` | Next State | Output `seq_detected` (next clk) |
|---|---|---|---|
| `S_IDLE` (00) | 0 | `S_IDLE` | 0 |
| `S_IDLE` (00) | 1 | `S_1` | 0 |
| `S_1` (01) | 0 | `S_10` | 0 |
| `S_1` (01) | 1 | `S_1` | 0 |
| `S_10` (10) | 0 | `S_IDLE` | 0 |
| `S_10` (10) | 1 | `S_101` | 0 |
| `S_101` (11) | 0 | `S_10` | 0 |
| `S_101` (11) | 1 | `S_1` | 1 |

## Verification
Verified with `tb_sequence_detector.v` covering directed tests, overlapping patterns, back-to-back matches, asynchronous reset assertion during active tracking, and reset recovery.
