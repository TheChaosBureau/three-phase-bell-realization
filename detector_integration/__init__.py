"""Detector-layer integration between linear front-ends and detector races."""

from .frontends.four_branch import four_branch_weights
from .frontends.two_branch import two_branch_weights
from .sim.run_four_branch_integration import run_chsh_trials, run_four_branch_trials
from .sim.run_two_branch_integration import run_two_branch_trials

__all__ = [
    "four_branch_weights",
    "run_chsh_trials",
    "run_four_branch_trials",
    "run_two_branch_trials",
    "two_branch_weights",
]
