from __future__ import annotations

from pathlib import Path


def hardware_parts_list() -> list[dict[str, str]]:
    return [
        {"item": "Matched branch absorber", "quantity": "2", "notes": "50 ohm terminated absorber pad at each detector input"},
        {"item": "Bias trim DAC or pot", "quantity": "2", "notes": "Sets near-threshold rare-event operating point per cell"},
        {"item": "Metastable avalanche or latch core", "quantity": "2", "notes": "Near-threshold trigger element biased below deterministic firing"},
        {"item": "Fast comparator or sense amplifier", "quantity": "2", "notes": "Converts nucleation onset into a digital pulse"},
        {"item": "One-shot pulse shaper", "quantity": "2", "notes": "Guarantees one clean output pulse per successful trigger"},
        {"item": "Reset switch", "quantity": "2", "notes": "MOSFET or current sink used to quench and reset each cell"},
        {"item": "Two-way power splitter", "quantity": "1", "notes": "Generates matched branch drives from one calibrated source"},
        {"item": "Step attenuator or variable pad", "quantity": "2", "notes": "Trims absorbed power and balances branch gain"},
        {"item": "Timestamp counter", "quantity": "1", "notes": "Captures first-click winner and pulse timing"},
        {"item": "Oscilloscope or fast digitizer", "quantity": "1", "notes": "Captures pulse overlays, jitter, and reset behavior"},
    ]


def detector_cell_candidate_markdown() -> str:
    return "\n".join(
        [
            "# Detector-Cell Candidate",
            "",
            "Candidate class: matched branch absorber feeding a near-threshold avalanche or metastable latch stage, followed by a pulse shaper and explicit reset path.",
            "",
            "## Rationale",
            "",
            "- The repo's reduced-model work favors shot-trigger / rare-event nucleation over accumulator-style detectors.",
            "- A matched absorber can turn branch power into microscopic trigger opportunities.",
            "- A metastable internal node provides the irreversible one-click transition once one microscopic opportunity succeeds.",
            "- A one-shot output stage enforces a clean digital pulse for the later common-mode latch.",
            "",
            "## Candidate Schematic",
            "",
            "```text",
            "branch drive -> 50 ohm absorber -> metastable avalanche/latch core -> fast comparator -> one-shot pulse -> winner line",
            "                                      ^                               |",
            "                                      |                               +-> timestamp monitor",
            "                                      +---- bias trim / quench reset <-+",
            "```",
            "",
            "## Contract",
            "",
            "- No deterministic switching at nominal bias.",
            "- Rare stochastic firing with click rate approximately lambda_dark + alpha * P_abs over the calibrated window.",
            "- One clean output pulse per successful nucleation.",
            "- Explicit reset path and measurable dead time.",
            "",
        ]
    )


def two_cell_block_diagram_markdown() -> str:
    return "\n".join(
        [
            "# Two-Cell Test-Rig Block Diagram",
            "",
            "```text",
            "calibrated RF/power source",
            "        |",
            "        v",
            "  fixed attenuator -> directional coupler -> 2-way splitter",
            "                                         |               |",
            "                                         v               v",
            "                                  trim attenuator A  trim attenuator B",
            "                                         |               |",
            "                                         v               v",
            "                                   detector cell A  detector cell B",
            "                                         |               |",
            "                                         +------ timestamp / winner capture ------+",
            "                                                         |",
            "                                                         v",
            "                                              scope + click counter + reset control",
            "```",
            "",
            "Both branches use the same source and nominally identical absorbers so the injected power split is the only intended asymmetry during race runs.",
            "",
        ]
    )


def bias_reset_scheme_markdown() -> str:
    return "\n".join(
        [
            "# Biasing And Reset Scheme",
            "",
            "- Each cell has an independent fine bias trim so the metastable operating point can be centered in the rare-event regime.",
            "- Bias is swept first with no signal to identify quiet, rare-event, and self-firing regions.",
            "- A reset switch momentarily quenches the metastable node after each click, then releases it after a fixed holdoff.",
            "- Winner capture logic masks further pulses until reset has completed, preventing double counting during dead time.",
            "",
            "Recommended bench sequence:",
            "",
            "1. Set both cells below threshold and verify no deterministic switching.",
            "2. Sweep bias upward at zero input to map dark-count onset.",
            "3. Lock each cell at the selected rare-event bias point.",
            "4. Apply reset holdoff longer than the measured recovery-90 interval before accepting the next trial.",
            "",
        ]
    )


def input_drive_setup_markdown() -> str:
    return "\n".join(
        [
            "# Calibrated Input-Drive Setup",
            "",
            "- Use one calibrated source feeding a two-way splitter so both branches share the same amplitude reference.",
            "- Insert a fixed attenuator ahead of the splitter to improve source match and keep the splitter in a linear regime.",
            "- Use branch trim attenuators after the splitter to equalize absorbed power during matching runs.",
            "- Verify absorbed power at each branch with the detector disconnected and a matched termination installed.",
            "- For race tests, keep total absorbed power fixed and change only the branch split fractions.",
            "",
            "Suggested benchmark splits: 0.50/0.50, 0.60/0.40, 0.70/0.30, and 0.75/0.25.",
            "",
        ]
    )


def write_hardware_deliverables(outdir: Path) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    schematic_path = outdir / "detector_cell_candidate.md"
    block_path = outdir / "two_cell_test_rig_block_diagram.md"
    bias_path = outdir / "bias_reset_scheme.md"
    drive_path = outdir / "input_drive_setup.md"
    bom_path = outdir / "parts_list.csv"

    schematic_path.write_text(detector_cell_candidate_markdown() + "\n", encoding="utf-8")
    block_path.write_text(two_cell_block_diagram_markdown() + "\n", encoding="utf-8")
    bias_path.write_text(bias_reset_scheme_markdown() + "\n", encoding="utf-8")
    drive_path.write_text(input_drive_setup_markdown() + "\n", encoding="utf-8")

    bom_rows = hardware_parts_list()
    bom_lines = ["item,quantity,notes"]
    bom_lines.extend(f"{row['item']},{row['quantity']},{row['notes']}" for row in bom_rows)
    bom_path.write_text("\n".join(bom_lines) + "\n", encoding="utf-8")

    return {
        "schematic_md": str(schematic_path),
        "block_diagram_md": str(block_path),
        "bias_reset_md": str(bias_path),
        "input_drive_md": str(drive_path),
        "parts_csv": str(bom_path),
    }
