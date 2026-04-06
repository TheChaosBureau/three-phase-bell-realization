## actual_spice_front_end

Build the first actual SPICE netlist for the shared front-end and validate it against the frozen preferred-chain baseline

## Objective

Create the first **actual SPICE-executed front-end milestone** for the shared resonant measurement program.

This ticket must answer:

1. Can the current preferred front-end be translated into a real SPICE netlist that runs in an actual circuit simulator?
2. Can that SPICE front-end produce probeable transient branch waveforms:

   * node voltages,
   * branch currents,
   * branch powers,
   * integrated branch energies?
3. Do the resulting branch energy fractions match the frozen preferred-chain front-end benchmark closely enough to justify using SPICE-generated traces as the new upstream artifact?

This ticket is intentionally **front-end only**.

It does **not** require:

* detector in SPICE,
* latch in SPICE,
* closure/drain in SPICE.

The downstream measurement stack remains frozen and external for now.

---

## Background

The current preferred chain has already been validated through:

* resonant/shared-mode front-end refinement
* explicit component-level front-end netlist candidate
* integrated front-end + closure co-design
* selected subblock device-level physicalization
* frozen detector boundary
* frozen detector family
* frozen winner latch
* frozen closure/drain semantics

The current preferred-chain baseline is strong enough to serve as the reference benchmark for SPICE translation.

The key motivation for this ticket is alignment with the actual desired artifact:

> a real circuit simulation that can be probed and analyzed directly.

Up to now, the work has been:

* SPICE-facing,
* SPICE-style,
* explicit component-level,
* but not yet **actual SPICE execution**.

This ticket is the first deliberate crossing of that boundary.

---

## Scope

Included:

* first actual SPICE netlist for the shared front-end
* explicit component values and topology
* transient simulation in a real SPICE engine
* extraction of branch voltages, currents, powers, and integrated energies
* comparison against the frozen preferred-chain front-end baseline
* export of SPICE branch traces in a format suitable for later downstream use

Excluded:

* detector in SPICE
* latch in SPICE
* closure/drain in SPICE
* full-chain SPICE execution
* downstream measurement semantics redesign
* production-quality device models unless convenient
* fabrication/layout concerns

---

## Frozen items for this ticket

Do **not** change these unless a hard front-end/SPICE issue forces it:

### Frozen benchmark cases

Use the same benchmark shared-state preparation and analyzer settings as the current preferred-chain baseline.

### Frozen comparison target

Use the current preferred-chain front-end behavior as the reference:

* branch energy fractions
* benchmark angle cases
* front-end pass thresholds

### Frozen downstream boundary (for future handoff only)

Do not use this ticket to redesign the downstream interface:

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

These remain frozen but are **not** the main subject of this ticket.

---

## Design intent

The purpose of this ticket is to move from:

* explicit component-level front-end candidate in Python-side modeling

to:

* actual SPICE netlist run in a real simulator

while preserving the same physical interpretation:

* shared resonant structure
* analyzer/readout dependence
* measurable branch outputs
* branch-energy comparison to the current preferred baseline

The output of this ticket should be:

* a real SPICE file,
* real transient data,
* real probeable nodes/branches,
* and a clean comparison to the current baseline.

---

## SPICE engine expectations

The implementation must use an actual circuit simulator, such as:

* ngspice
* Xyce
* LTspice-compatible format if runnable in the environment
* or another explicitly documented real SPICE engine

The report must clearly state:

* which engine was used
* how the simulation was run
* what netlist dialect/compatibility assumptions were made

---

## Candidate implementation directions

Choose one and document why.

### Option A — Direct translation of the explicit front-end netlist candidate

Translate the current component-level front-end candidate as directly as possible into SPICE syntax.

Preferred first pass.

### Option B — Simplified but equivalent SPICE front-end

Implement a simpler SPICE front-end that preserves the key front-end behavior while staying close to the explicit candidate.

Acceptable if direct translation is awkward.

### Option C — Hybrid SPICE front-end with explicit preparation wrapper

Use an explicit SPICE front-end netlist while keeping preparation or analyzer configuration partially scripted around the netlist.

Acceptable if needed for the first milestone.

---

## Functional requirements

### FR1 — Actual SPICE netlist exists

Produce at least one real SPICE netlist file representing the shared front-end.

### FR2 — Netlist runs successfully

The SPICE netlist must execute successfully in a real simulator with a transient analysis that produces probeable waveforms.

### FR3 — Four measurable branch outputs

The front-end must expose four measurable branches:

* `++`
* `+-`
* `-+`
* `--`

For each branch, the simulation or post-processing must provide:

* voltage
* current
* instantaneous power
* integrated absorbed energy

### FR4 — Shared resonant/coupled structure is explicit

The front-end netlist must contain explicit front-end component structure (e.g. R/L/C/coupling elements or equivalent netlist-level constructs), not just direct behavioral branch-weight assignment.

### FR5 — Benchmark fidelity

Across benchmark cases, normalized branch energies
[
f_k=\frac{E_k}{\sum_j E_j}
]
must remain close to the current preferred-chain front-end target.

### FR6 — Probeability

The resulting simulation must be probeable in the normal SPICE sense:

* named nodes and/or branch elements
* waveforms that can be inspected directly
* no hidden-only internal outputs without documentation

### FR7 — Export for later downstream use

The SPICE-generated branch traces must be exported in a structured format suitable for later detector-boundary handoff, even if that handoff is not yet part of this ticket.

---

## Inputs / outputs

### Inputs

* shared-state preparation parameters or equivalent source configuration
* analyzer settings ((a,b))
* benchmark angle sets
* explicit component values
* SPICE engine configuration

### Outputs

* actual SPICE netlist(s)
* transient waveform files or exported data
* branch voltage traces
* branch current traces
* branch power traces
* integrated branch energies
* normalized branch fractions
* comparison against the frozen preferred-chain front-end baseline

---

## Deliverables

### Netlist / simulation deliverables

* [ ] actual SPICE netlist for the shared front-end
* [ ] run script or documented simulator invocation
* [ ] transient output export
* [ ] branch-energy post-processing script
* [ ] benchmark comparison script

### Artifact deliverables

* [ ] `artifacts/actual_spice_front_end/netlist/`
* [ ] `artifacts/actual_spice_front_end/raw_waveforms/`
* [ ] `artifacts/actual_spice_front_end/processed_traces/`
* [ ] `artifacts/actual_spice_front_end/front_end_metrics/`
* [ ] `artifacts/actual_spice_front_end/summary_report.md`
* [ ] `artifacts/actual_spice_front_end/summary_metrics.json`
* [ ] `artifacts/actual_spice_front_end/summary_metrics.csv`
* [ ] `artifacts/actual_spice_front_end/design_note.md`

### Required design note

* [ ] `design_note.md`

This note must include:

* chosen SPICE engine
* chosen netlist architecture
* how preparation is represented
* how analyzer dependence is represented
* how the four branches are measured
* what remains abstract outside the netlist
* what compromises were made for the first SPICE milestone

---

## Required plots

* [ ] netlist topology / node map diagram
* [ ] representative branch voltage traces
* [ ] representative branch current traces
* [ ] representative branch power traces
* [ ] exact vs SPICE branch energy fractions
* [ ] benchmark-case comparison summary
* [ ] residual/error summary plot

---

## Quantitative acceptance criteria

### A. Front-end branch-fraction fidelity

Across benchmark cases:

* [ ] RMS four-branch energy-fraction error < 0.03
* [ ] max four-branch energy-fraction error < 0.05

### B. Netlist execution

* [ ] actual SPICE netlist runs successfully for the benchmark cases
* [ ] output traces are exportable and finite

### C. Probeability

* [ ] node voltages and branch currents are inspectable directly
* [ ] the report clearly documents what to probe

### D. Architectural explicitness

* [ ] no trivial direct exact-weight fallback
* [ ] the SPICE front-end is recognizably more than a placeholder behavioral wrapper

---

## Benchmark cases

### Shared-state benchmark

Use the same shared preparation target as the current preferred-chain baseline.

### Angle benchmarks

At minimum:

* [ ] (a=0^\circ,\ b=0^\circ)
* [ ] (a=45^\circ,\ b=22.5^\circ)
* [ ] (a=0^\circ,\ b=45^\circ)

### CHSH benchmark set

Also run the standard CHSH angle set as front-end-only cases:
[
a_0=0^\circ,\quad a_1=45^\circ,\quad b_0=22.5^\circ,\quad b_1=-22.5^\circ
]

This ticket does **not** yet require full CHSH evaluation through the downstream chain, but the front-end traces for those settings should be generated and archived.

---

## Experimental / simulation plan

### Task 1 — Choose SPICE architecture and engine

Select the real SPICE engine and the translation approach (Option A, B, or C).

**Output**

* `design_note.md`

### Task 2 — Build the actual SPICE front-end netlist

Implement the front-end as a real SPICE netlist with explicit component values and probeable branches.

**Output**

* netlist files
* run instructions
* raw waveform outputs

### Task 3 — Export branch traces

Extract:

* branch voltages
* branch currents
* branch powers
* integrated energies

Store them in a structured format.

**Output**

* processed trace files
* energy summary CSV

### Task 4 — Compare to the frozen front-end baseline

For each benchmark case:

* compute normalized SPICE branch fractions
* compare against the current preferred-chain front-end target
* report RMS/max error

**Output**

* comparison CSV
* comparison plots

### Task 5 — Archive detector-boundary-ready traces

Export the SPICE branch traces in a format suitable for later downstream use by the frozen detector boundary.

**Output**

* detector-boundary-ready trace files
* interface note

---

## Tests

Add tests for:

### T1

SPICE netlist files are generated correctly.

### T2

The benchmark simulations run successfully.

### T3

Extracted branch traces are finite and nonempty.

### T4

Integrated branch energies are computed consistently.

### T5

Benchmark fraction errors remain within acceptance.

### T6

The implementation is not reducible to trivial exact-weight assignment.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] the netlist does not run successfully in a real SPICE engine
* [ ] branch traces are not probeable or exportable
* [ ] branch energy fractions degrade beyond acceptance
* [ ] the implementation relies on hidden direct exact-weight assignment
* [ ] the result is not meaningfully more “actual SPICE” than the current baseline

---

## Decision gate after this ticket

Proceed only if:

1. a real SPICE front-end netlist exists and runs,
2. it reproduces benchmark branch fractions acceptably,
3. its outputs are probeable and exportable,
4. it is ready to serve as the upstream artifact for the next downstream handoff milestone.

If these pass, the next ticket should be:

**Drive the frozen detector/latch/closure stack from actual SPICE-generated front-end traces and validate the first SPICE-driven preferred-chain benchmark.**

If they fail, iterate on the SPICE front-end translation before proceeding downstream.

---

## Suggested labels

`research`
`spice`
`front-end`
`netlist`
`milestone`
`integration`
`high-priority`

---

## Summary

**Build the first actual SPICE netlist for the shared front-end and validate it against the frozen preferred-chain front-end benchmark**
