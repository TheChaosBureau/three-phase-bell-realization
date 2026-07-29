# three-phase-bell-realization
Classical three-phase Bell-violation realization (SPICE + detector chain) — paper: *Bell Violations as Three-Party Quadratic Conservation*. Spun off from three-phase-entanglement.

## Published paper

**[Bell Violations as Three-Party Quadratic Conservation: A Classical Three-Phase Realization](https://davidnobles-eng.github.io/papers/three-phase-bell-realization.html)**
— [direct PDF](https://davidnobles-eng.github.io/assets/three-phase-bell-realization.pdf), 64 pp.

That PDF is built from this repo: `nix develop -c make paper`, which writes
`paper/paper.pdf` and `artifacts/paper/paper.pdf`.

Scope: the construction requires a non-local conservation constraint and
therefore does **not** refute Bell's theorem, and is not offered as a local
hidden-variable model.

## Quickstart

**NixOS (recommended)**
- `nix develop`
- drops you into a poetry shell with the python deps installed

**Non-NixOS or user-controlled env**
- Just do `poetry install`
- This is functionally similar to `pip install requirements`

**Open the paper**
- `paper/paper.qmd` or `paper/paper.ipynb` (same thing, different formats)

## Context
- This is not a package, but the following files capture env dependencies for deterministic reproducibility
- There are **two layers** of environment and dependency management:
    - `flake.nix` for shell packages (eg poetry, python)
    - `pyproject.toml` once inside shell, for python deps (eg matplotlib, numpy)

## Git hook
- Run `git config core.hooksPath .githooks` once per clone so commits use the repository hook directory.
- The `pre-commit` hook in `.githooks/` calls `scripts/clear_notebook_outputs.py` to strip outputs and execution counts from any staged `.ipynb` files, then restages them automatically before the commit proceeds.


## Running stuff

  The Make target is in Makefile:74. Default usage:

  make detector-search

  Useful overrides:

  make detector-search DETECTOR_MODEL=shot_trigger DETECTOR_SAMPLES=50
  make detector-search DETECTOR_MODEL=poisson_linear DETECTOR_SAMPLES=10 DETECTOR_OUTDIR=artifacts/detector_search/
  poisson_run

  Direct CLI examples:

  poetry run python -m detector_search.experiments.run_rate_scan poisson_linear \
    --params '{"lambda_dark": 0.02, "alpha": 0.8, "dead_time": 0.0}' \
    --outdir artifacts/detector_search/rate_scan

  poetry run python -m detector_search.experiments.run_race_scan shot_trigger \
    --params '{"eps_event": 1.25, "p_trig": 0.9, "lambda_dark": 0.02, "dead_time": 0.0}' \
    --outdir artifacts/detector_search/race_scan

  poetry run python -m detector_search.experiments.run_global_search shot_trigger \
    --samples 20 \
    --jsonl artifacts/detector_search/shot_trigger/results.jsonl \
    --csv artifacts/detector_search/shot_trigger/results.csv \
    --outdir artifacts/detector_search/shot_trigger
---

*Spun off from [`three-phase-entanglement`](https://github.com/TheChaosBureau/three-phase-entanglement) on 2026-06-29 during a branch consolidation (source branch `born-exploration`); the `wavepool` simulator is vendored under `sim/`. Full git history is preserved here, and the original branch tip is tagged `archive/born-exploration` on the parent repo.*
