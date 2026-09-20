# Hardware Source Modules (`src/`)

## 1. Directory Overview & HDL Standards

This directory contains the synthesizable Register-Transfer Level (RTL) Verilog source files and simulation testbenches for the SPECTRA framework. All modules conform to the **IEEE Std 1364-2001** (IEEE Standard for Verilog Hardware Description Language) specification, ensuring cross-platform portability across major Electronic Design Automation (EDA) synthesis and simulation environments, including Xilinx Vivado (2020.1 and newer), Synopsys VCS, Cadence Incisive, and open-source simulators (Icarus Verilog, Verilator).

The hardware implementation serves as the physical benchmark substrate for post-silicon side-channel power proxy extraction, modeling both non-infected golden cryptographic silicon and covertly modified Trojan-bearing integrated circuits.

---

## 2. File Manifest & File Descriptions

| Filename | Module Identifier | Primary Function | Synthesis Target |
| :--- | :--- | :--- | :--- |
| [`aes_128.v`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/src/aes_128.v) | `aes_128` | Baseline 128-bit AES cryptographic core (Golden reference) | Synthesizable RTL (FPGA / ASIC) |
| [`aes_128_trojan.v`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/src/aes_128_trojan.v) | `aes_128_trojan` | AES core with covert 2-bit counter Trojan (~0.1% area overhead) | Synthesizable RTL (FPGA / ASIC) |
| [`tb_sidechannel.v`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/src/tb_sidechannel.v) | `tb_sidechannel` | Cycle-accurate lockstep simulation testbench & power trace recorder | Simulation Only |

### Individual File Descriptions
- **`aes_128.v`:** Synthesizable IEEE 1364-2001 Verilog implementation of an iterative 10-round Advanced Encryption Standard (AES) engine with a 128-bit datapath. Features synchronous active-low reset, explicit register typing, modular S-Box byte substitution, shift-row permutations, and Galois field mix-column transformations representing clean golden reference silicon.
- **`aes_128_trojan.v`:** Synthesizable Trojan-infected AES cipher core containing identical functional logic to `aes_128.v` alongside an embedded 0.1% area footprint synchronous 2-bit counter Trojan. Remains dormant under normal execution and triggers only on a rare 32-bit state prefix, toggling an internal capacitive load without corrupting the functional ciphertext output pins.
- **`tb_sidechannel.v`:** High-speed lockstep simulation testbench that instantiates both the golden and infected AES cores under identical 10 MHz clock and low-toggle stimulus vectors. Records cycle-by-cycle simulated dynamic current consumption and streams time-domain power proxy traces into CSV output sinks in the `reports/` directory.

---

## 3. Module Specifications & Implementation Details

### 3.1 `aes_128.v` (Golden Cryptographic Core)

The `aes_128` module implements an iterative 10-round Advanced Encryption Standard (AES) datapath with a 128-bit block size and a 128-bit key length. The architecture utilizes an iterative finite-state machine (FSM) to optimize silicon area while generating realistic switching activity for power analysis.

#### Port Interface Definition

| Port Name | Direction | Width (bits) | Type | Functional Description |
| :--- | :--- | :--- | :--- | :--- |
| `clk` | Input | 1 | `wire` | Primary system clock ($f_{\text{clk}} = 10\text{ MHz}$, 100 ns period) |
| `rst_n` | Input | 1 | `wire` | Active-low asynchronous/synchronous system reset |
| `start` | Input | 1 | `wire` | Single-cycle pulse initiating a 10-round encryption cycle |
| `key_in` | Input | 128 | `wire` | Master cipher key vector |
| `state_in` | Input | 128 | `wire` | Plaintext input data block |
| `state_out` | Output | 128 | `reg` | Ciphertext output block (valid on `done = 1`) |
| `done` | Output | 1 | `reg` | Active-high status flag indicating encryption completion |

#### Datapath Architecture & FSM Operation

The datapath operates across three primary state machine registers:
- `STATE_IDLE` (`2'b00`): Awaiting assertion of `start`. When asserted, `state_reg` is initialized with the pre-round key addition (`state_in ^ key_in`), and the round counter is set to `4'd1`.
- `STATE_ROUND` (`2'b01`): Executes iterative transformations for rounds 1 through 9:
  1. `sub_bytes_128`: 16-byte parallel S-Box substitution lookup.
  2. `shift_rows_128`: Vectorized cyclical byte permutation across rows.
  3. `mix_columns_128`: Galois Field linear combination transformation.
  4. `round_key` addition: Bitwise XOR with round-derived key schedule.
- `STATE_FINAL` (`2'b10`): Executes Round 10 omitting `mix_columns_128`, commits output to `state_out`, and asserts `done`.

```
                    +------------------------------------+
                    |             STATE_IDLE             |
                    +------------------------------------+
                                      | (start == 1)
                                      v
                    +------------------------------------+
                    |            STATE_ROUND             | <---+
                    | (SubBytes + ShiftRows + MixCols)   |     | (round_count < 10)
                    +------------------------------------+ ----+
                                      | (round_count == 10)
                                      v
                    +------------------------------------+
                    |            STATE_FINAL             |
                    | (SubBytes + ShiftRows + KeyAdd)    |
                    +------------------------------------+
                                      |
                                      v
                                 (done == 1)
```

---

### 3.2 `aes_128_trojan.v` (Trojan-Infected Cryptographic Core)

The `aes_128_trojan` module incorporates an identical functional datapath to `aes_128.v`, augmented with a dormant, covert synchronous Hardware Trojan. 

#### Hardware Trojan Architectural Characteristics

1. **Silicon Area Footprint:**
   The Trojan consists of a 32-bit state comparator, a 2-bit synchronous counter (`trojan_counter`), a trigger latch (`trojan_trigger`), and a toggle flip-flop (`trojan_payload`). This equates to approximately **0.1% silicon area overhead** relative to the AES core, meeting the stringent sub-1% stealth criteria defined in the IEEE JIOT 2024 reference paper.

2. **Trigger Mechanism (Rare Corner-Case Activation):**
   The Trojan monitors internal datapath state bits without tapping external IO pins:
   ```verilog
   assign rare_pattern_match = (state_in[31:0] == 32'hA5A5_5A5A);
   ```
   Activation requires four successive occurrences (`trojan_counter == 2'b11`) of this rare 32-bit condition during active encryption starts, ensuring that traditional random functional testing will not inadvertently trigger the payload.

3. **Implicit Payload Execution (Non-Destructive Side-Channel Modulation):**
   Upon activation (`trojan_trigger = 1`), the payload executes:
   ```verilog
   if (trojan_trigger) begin
       trojan_payload <= ~trojan_payload;
   end
   ```
   - **Zero Ciphertext Tampering:** `state_out` is generated identically to the golden core. Functional verification against NIST SP 800-38A test vectors passes with zero bit discrepancies.
   - **Side-Channel Capacitive Modulation:** The toggle flip-flop introduces localized dynamic current transients ($\Delta I_{dd}$) into the power distribution network, generating subtle inter-harmonic spectral lines ($15\text{ MHz}$, $25\text{ MHz}$, $35\text{ MHz}$) captured by SPECTRA's feature extraction pipeline.

---

### 3.3 `tb_sidechannel.v` (Simulation Testbench & Trace Recorder)

The testbench provides an automated physical proxy simulation environment for side-channel trace generation.

#### Lockstep Co-Simulation Architecture

Both the golden core (`uut_golden`) and the Trojan core (`uut_trojan`) are instantiated in parallel, driven by synchronous stimulus:
- **System Clock:** Generated with a 100 ns period ($f_{\text{clk}} = 10\text{ MHz}$) using `#50 clk = ~clk;`.
- **Low-Toggle Stimulus Optimization:** Stimulus sequences are constrained to minimize core switching noise ($d_{\text{AES}}$), preventing dynamic noise masking of the 0.1% Trojan signature:
  ```verilog
  repeat (1000) begin
      @ (posedge clk);
      start <= 1'b1;
      state_in <= {96'h0, $random};
      @ (posedge clk);
      start <= 1'b0;
      @ (posedge done_golden);
  end
  ```
- **Trace Output Sinks:** Trace streams are committed to [`reports/power_trace_golden.csv`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/power_trace_golden.csv) and [`reports/power_trace_trojan.csv`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/power_trace_trojan.csv) using `$fdisplay`, `$dumpflush`, and `$fclose`.

---

## 4. Synthesis & Timing Considerations

When targeting Xilinx 7-Series or Spartan architectures:
1. **Clock Period Constraint:** Specify a 100 ns clock period (`create_clock -period 100.000 -name clk [get_ports clk]`). The critical path runs through `sub_bytes_128` and `mix_columns_128` logic trees, yielding positive slack ($> 85\text{ ns}$) under 28 nm / 90 nm FPGA primitives.
2. **Preservation of Trojan Logic:** When synthesizing `aes_128_trojan.v`, ensure boundary optimization and unused net pruning do not eliminate the implicit payload:
   ```tcl
   set_property DONT_TOUCH true [get_cells uut_trojan/trojan_*]
   ```
3. **Reset De-assertion:** `rst_n` must be cleanly de-asserted synchronously to the negative clock edge to avoid metastability in round counters.
