from __future__ import annotations

from pathlib import Path

from detector_rig.config import LatchRigConfig


def latch_block_diagram_markdown(config: LatchRigConfig) -> str:
    return "\n".join(
        [
            "# Winner Latch Block Diagram",
            "",
            "```text",
            "detector cell A one-shot ----> edge capture A ----+",
            "                                                  |",
            "                                                  v",
            "                                            +-----------+",
            "reset / trial gate ------------------------> | SR latch  | ----> winner_A",
            "                                            |  arbiter  | ----> winner_B",
            "detector cell B one-shot ----> edge capture B ----+     | ----> winner_valid",
            "                                                  |     | ----> mask_A / mask_B",
            "                                                  +-----+ ----> winner_line -> future drain / closure block",
            "```",
            "",
            "## Interface",
            "",
            "- Inputs: `A_pulse`, `B_pulse`, `reset`, optional `trial_gate`.",
            "- Outputs: `winner_A`, `winner_B`, `winner_valid`, `mask_A`, `mask_B`, and a placeholder `winner_line` for the future drain network.",
            "- Design intent: detector cells stay responsible for rare-event selection; the latch only enforces exclusivity after the first valid pulse arrives.",
            "",
            "## Timing Contract",
            "",
            f"- Minimum accepted pulse width: {config.min_input_pulse_width_ns:.2f} ns.",
            f"- Input threshold: {config.input_threshold_v:.2f} V.",
            f"- Pickoff delay into the arbiter: {config.pickoff_delay_ns:.2f} ns.",
            f"- Latch propagation delay: {config.propagation_delay_ns:.2f} ns.",
            f"- Mutual inhibition asserted within {config.inhibit_delay_ns:.2f} ns of winner capture.",
            f"- Guaranteed settled winner state within {config.settle_time_ns:.2f} ns.",
            f"- Tie region: arrivals within +/-{config.tie_window_ns:.2f} ns resolve deterministically to {config.tie_break_priority}.",
            f"- Hold until reset, then re-arm after {config.rearm_holdoff_us:.2f} us holdoff.",
            "",
        ]
    )


def latch_schematic_markdown(config: LatchRigConfig) -> str:
    return "\n".join(
        [
            "# Winner Latch Logic Design",
            "",
            "First implementation: pulse-shaped detector outputs feed a mutually exclusive SR-latch / arbiter with fixed-priority tie resolution inside a narrow aperture. The latch is post-click only and does not bias the detector cells before a click.",
            "",
            "## Logic Sketch",
            "",
            "```text",
            "A_pulse -> comparator / pulse shaper -> set_A ----+",
            "                                                 |",
            "                                                 v",
            "                                         +---------------+",
            "                                         | cross-coupled |----> winner_A",
            "B_pulse -> comparator / pulse shaper -> set_B ----+ NOR  |----> winner_B",
            "                                                   latch  |----> winner_valid = winner_A OR winner_B",
            "reset -------------------------------------------> reset |",
            "                                         +---------------+",
            "winner_A -----------------------------------------------> mask_B",
            "winner_B -----------------------------------------------> mask_A",
            "winner_A / winner_B ------------------------------------> winner_line placeholder",
            "```",
            "",
            "## Tie Handling",
            "",
            f"- If both set inputs arrive outside the +/-{config.tie_window_ns:.2f} ns aperture, the earlier edge wins.",
            f"- Inside the aperture, `{config.tie_break_priority}` has fixed priority so no undefined persistent state is exposed.",
            f"- Because the aperture is sub-nanosecond while detector race times are millisecond-scale, the priority rule is documented but negligibly small in the measured race-law budget.",
            "",
            "## Reset / Holdoff",
            "",
            f"- Reset actively clears the latch for {config.reset_pulse_ns:.2f} ns.",
            f"- New winner requests are ignored until the combined reset + holdoff interval of {config.reset_pulse_ns / 1000.0 + config.rearm_holdoff_us:.3f} us has elapsed.",
            "",
        ]
    )


def write_latch_hardware_deliverables(outdir: Path, config: LatchRigConfig) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    block_path = outdir / "latch_block_diagram.md"
    schematic_path = outdir / "latch_schematic.md"

    block_path.write_text(latch_block_diagram_markdown(config) + "\n", encoding="utf-8")
    schematic_path.write_text(latch_schematic_markdown(config) + "\n", encoding="utf-8")

    return {
        "block_diagram_md": str(block_path),
        "schematic_md": str(schematic_path),
    }
