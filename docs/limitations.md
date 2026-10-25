# AutoSilix Known Limitations & Boundary Conditions

## 1. Physical Signoff & Tape-out Readiness Disclaimer

> [!CAUTION]
> **A generated GDSII layout stream does NOT constitute tape-out or fabrication readiness.**
> AutoSilix automates digital implementation pipelines using open-source tools. Manufacturing readiness requires foundry signoff DRC/LVS decks, comprehensive multi-corner static timing analysis, electromigration (EM), IR drop analysis across temperature corners, and tape-out design reviews.

## 2. Power Analysis Scope
Dynamic and leakage power estimation requires standard-cell power characterization libraries (Liberty `.lib`), accurate activity profiles (VCD/SAIF switching activity), and validated operating voltage conditions. In the current release, power metrics are labeled unavailable unless accompanied by valid simulation vectors.

## 3. Platform & Flow Portability
The reference flow scripts currently target the SkyWater SKY130 high-density standard-cell library (`sky130_fd_sc_hd`). GF180MCU and other open PDK platforms are planned roadmap targets and should not be expected to function as drop-in replacements without customized layer mappings and cell libraries.

## 4. Concurrent Execution
Workflow stages are executed in sequential dependency order. Parallel branch execution (e.g. concurrent synthesis exploration across multiple strategies) is planned for future releases.
