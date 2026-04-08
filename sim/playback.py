from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .io import write_dataframe, write_json
from .renderer import render_playback


def export_trial_playback(
    trial_index: int,
    timeseries: pd.DataFrame,
    summary: dict[str, Any],
    outdir: str | Path,
    playback_mode: str = "truth_preserving",
    fps: int = 30,
    sample_interval: float = 0.01,
) -> dict[str, Path]:
    output_root = Path(outdir)
    timeseries_path = output_root / f"trial_{trial_index}_timeseries.csv"
    playback_path = output_root / f"trial_{trial_index}_playback.mp4"
    metadata_path = output_root / f"trial_{trial_index}_playback.json"

    write_dataframe(timeseries, timeseries_path)
    metadata = render_playback(
        timeseries=timeseries,
        summary=summary,
        output_path=playback_path,
        playback_mode=playback_mode,
        fps=fps,
        sample_interval=sample_interval,
    )
    metadata["trial_index"] = trial_index
    write_json(metadata, metadata_path)
    return {
        "timeseries": timeseries_path,
        "playback": playback_path,
        "metadata": metadata_path,
    }
