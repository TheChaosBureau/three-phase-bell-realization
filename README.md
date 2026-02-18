# three-phase-entanglement
Interactive pedagogical paper for exploring quantum entanglement as modeled by three-phase power systems

## Quickstart

**NixOS (reccomended)**
- `nix develop`
- drops you into a poetry shell with the python deps installed

**Non-NixOS or user-controlled env**
- Just do `poetry install`
- This is functionally similar to `pip install requirements`

**Open the paper**
- `paper/paper.qmd` or `paper/paper.ipynb` (same thing, different formats)

## Context
- This is not a package, but the folowing files capture env dependencies for deterministic reproducibility
- There are **two layers** of environment and dependcy management:
    - `flake.nix` for shell packages (eg poetry, python)
    - `pyproject.toml` once inside shell, for python deps (eg matplotlib, numpy)

## Git hook
- Run `git config core.hooksPath .githooks` once per clone so commits use the repository hook directory.
- The `pre-commit` hook in `.githooks/` calls `scripts/clear_notebook_outputs.py` to strip outputs and execution counts from any staged `.ipynb` files, then restages them automatically before the commit proceeds.

## Prompts
- can you help me write the paper paper.qmd? it's just a rough draft right now. Rigorously write it and fill it out until it is ready for publication. It is a qmd file, so you can write python code which will generate figures, so include figures where appropriate. Pretend you are the author of this paper, a rigorous scientist.
