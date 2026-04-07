"""First physical/SPICE front-end candidate package."""

from typing import Any

from .boundary_calibration import CalibratedBoundaryConfig, freeze_boundary_note_data, resolved_calibrated_boundary_config
from .boundary_diagnosis import classify_boundary_outcome, selected_handoff_export_config
from .boundary_repro_check import PRIOR_DIAGNOSIS_REFERENCE, ReproCheckConfig, classify_reproducibility, resolved_repro_check_config
from .closure_path import (
    ClosureInterpretationConfig,
    closure_interpretations,
    run_four_branch_candidate_with_closure,
    simulate_four_branch_candidate_pre_click_race,
    simulate_post_click_closure,
)
from .common_inhibit_tuning import (
    CommonInhibitTuningSweepConfig,
    default_common_inhibit_tuning_sweep_config,
    evaluate_tuned_closure_config,
    run_common_inhibit_parameter_sweeps,
)
from .four_branch_candidate import FourBranchPhysicalFrontEndConfig, benchmark_four_branch_physical_cases, simulate_four_branch_physical_candidate
from .integration import materialize_candidate_trace, run_four_branch_candidate_handoff, run_four_branch_physical_chsh, run_four_branch_physical_handoff, run_two_branch_physical_handoff
from .metrics import aggregate_case_error, common_envelope_fidelity_metrics, correlator_rms_error, energy_preservation_metrics, finite_export_metrics, fraction_error_metrics
from .physical_closure_drain_candidate import (
    PhysicalClosureDrainConfig,
    default_physical_closure_drain_config,
    preferred_common_mode_interpretation,
    reduced_to_physical_mapping_summary,
    run_four_branch_candidate_with_physical_closure,
    simulate_physical_closure_drain,
    tuned_physical_closure_drain_config,
)
from .preferred_physical_chain import (
    preferred_physical_chain_benchmark_cases,
    run_preferred_physical_chain_benchmark,
    run_preferred_physical_chain_candidate,
    run_preferred_physical_chain_case,
)
from .preferred_physical_chain_lc import (
    CoupledPortLCFrontEndConfig,
    ExplicitLCCircuitClosureConfig,
    preferred_physical_chain_lc_benchmark_cases,
    run_preferred_physical_chain_lc_benchmark,
    run_preferred_physical_chain_lc_candidate,
    run_preferred_physical_chain_lc_case,
    simulate_explicit_lc_closure_drain,
    simulate_preferred_physical_chain_lc_candidate,
)
from .preferred_front_end_netlist_candidate import (
    FrontEndNetlistComponent,
    PreferredFrontEndNetlistConfig,
    preferred_front_end_netlist_benchmark_cases,
    run_preferred_front_end_netlist_benchmark,
    run_preferred_front_end_netlist_case,
    simulate_preferred_front_end_netlist_candidate,
)
from .preferred_chain_codesign import (
    PreferredChainCodesignConfig,
    preferred_chain_codesign_benchmark_cases,
    run_preferred_chain_codesign_benchmark,
    run_preferred_chain_codesign_candidate,
    run_preferred_chain_codesign_case,
    simulate_codesigned_closure_drain,
    simulate_preferred_chain_codesign_candidate,
)
from .preferred_chain_device_physicalization import (
    PreferredChainDevicePhysicalizationConfig,
    preferred_chain_device_physicalization_benchmark_cases,
    run_preferred_chain_device_physicalization_benchmark,
    run_preferred_chain_device_physicalization_candidate,
    run_preferred_chain_device_physicalization_case,
    simulate_device_physicalized_closure_drain,
    simulate_preferred_chain_device_physicalization_candidate,
)
from .actual_spice_front_end import (
    ActualSpiceFrontEndConfig,
    actual_spice_front_end_benchmark_cases,
    run_actual_spice_front_end_benchmark,
    run_actual_spice_front_end_case,
    simulate_actual_spice_front_end_candidate,
)
from .spice_driven_preferred_chain import (
    SpiceDrivenPreferredChainConfig,
    run_spice_driven_preferred_chain_benchmark,
    run_spice_driven_preferred_chain_candidate,
    run_spice_driven_preferred_chain_case,
    simulate_spice_driven_preferred_chain_candidate,
    spice_driven_preferred_chain_benchmark_cases,
)
from .spice_driven_robustness import (
    SpiceDrivenRobustnessConfig,
    run_spice_driven_robustness_sweep,
    spice_driven_robustness_points,
)
from .preferred_physical_chain_energy import build_trial_energy_accounting, summarize_energy_accounting_rows
from .preferred_physical_chain_metrics import build_chsh_result, build_pre_click_comparison, build_summary_metrics, summarize_post_click_behavior
from .refined_four_branch_candidate import RefinedSharedCoreFrontEndConfig, benchmark_refined_four_branch_cases, simulate_refined_four_branch_candidate
from .resonant_four_branch_candidate import ResonantSharedModeFrontEndConfig, benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate
from .two_branch_candidate import PhysicalFrontEndConfig, simulate_two_branch_physical_candidate


def build_physical_front_end_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_summary_report import build_physical_front_end_candidate_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_handoff_report(*args: Any, **kwargs: Any):
    from .experiments.build_handoff_report import build_physical_front_end_handoff_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_boundary_diagnosis_report(*args: Any, **kwargs: Any):
    from .experiments.build_boundary_diagnosis_report import build_physical_front_end_boundary_diagnosis_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_boundary_calibration_report(*args: Any, **kwargs: Any):
    from .experiments.build_boundary_calibration_report import build_physical_front_end_boundary_calibration_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_boundary_repro_check_report(*args: Any, **kwargs: Any):
    from .experiments.build_boundary_repro_check_report import build_physical_front_end_boundary_repro_check_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_four_branch_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_four_branch_candidate_report import build_physical_front_end_four_branch_candidate_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_four_branch_refined_report(*args: Any, **kwargs: Any):
    from .experiments.build_four_branch_refined_report import build_physical_front_end_four_branch_refined_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_four_branch_resonant_report(*args: Any, **kwargs: Any):
    from .experiments.build_four_branch_resonant_report import build_physical_front_end_four_branch_resonant_report as _build

    return _build(*args, **kwargs)


def build_post_click_closure_report(*args: Any, **kwargs: Any):
    from .experiments.build_post_click_closure_report import build_post_click_closure_report as _build

    return _build(*args, **kwargs)


def build_physical_closure_drain_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_physical_closure_drain_candidate_report import build_physical_closure_drain_candidate_report as _build

    return _build(*args, **kwargs)


def build_common_inhibit_tuning_report(*args: Any, **kwargs: Any):
    from .experiments.build_common_inhibit_tuning_report import build_common_inhibit_tuning_report as _build

    return _build(*args, **kwargs)


def build_preferred_physical_chain_report(*args: Any, **kwargs: Any):
    from .experiments.build_preferred_physical_chain_report import build_preferred_physical_chain_report as _build

    return _build(*args, **kwargs)


def build_preferred_physical_chain_lc_report(*args: Any, **kwargs: Any):
    from .experiments.build_preferred_physical_chain_lc_report import build_preferred_physical_chain_lc_report as _build

    return _build(*args, **kwargs)


def build_preferred_front_end_netlist_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_preferred_front_end_netlist_candidate_report import (
        build_preferred_front_end_netlist_candidate_report as _build,
    )

    return _build(*args, **kwargs)


def build_preferred_chain_codesign_report(*args: Any, **kwargs: Any):
    from .experiments.build_preferred_chain_codesign_report import (
        build_preferred_chain_codesign_report as _build,
    )

    return _build(*args, **kwargs)


def build_preferred_chain_device_physicalization_report(*args: Any, **kwargs: Any):
    from .experiments.build_preferred_chain_device_physicalization_report import (
        build_preferred_chain_device_physicalization_report as _build,
    )

    return _build(*args, **kwargs)


def build_actual_spice_front_end_report(*args: Any, **kwargs: Any):
    from .experiments.build_actual_spice_front_end_report import (
        build_actual_spice_front_end_report as _build,
    )

    return _build(*args, **kwargs)


def build_spice_driven_preferred_chain_report(*args: Any, **kwargs: Any):
    from .experiments.build_spice_driven_preferred_chain_report import (
        build_spice_driven_preferred_chain_report as _build,
    )

    return _build(*args, **kwargs)


def build_spice_driven_robustness_report(*args: Any, **kwargs: Any):
    from .experiments.build_spice_driven_robustness_report import (
        build_spice_driven_robustness_report as _build,
    )

    return _build(*args, **kwargs)


__all__ = [
    "ActualSpiceFrontEndConfig",
    "CalibratedBoundaryConfig",
    "actual_spice_front_end_benchmark_cases",
    "CommonInhibitTuningSweepConfig",
    "CoupledPortLCFrontEndConfig",
    "ClosureInterpretationConfig",
    "ExplicitLCCircuitClosureConfig",
    "FrontEndNetlistComponent",
    "FourBranchPhysicalFrontEndConfig",
    "PhysicalClosureDrainConfig",
    "PhysicalFrontEndConfig",
    "PreferredChainCodesignConfig",
    "PreferredChainDevicePhysicalizationConfig",
    "PreferredFrontEndNetlistConfig",
    "RefinedSharedCoreFrontEndConfig",
    "ResonantSharedModeFrontEndConfig",
    "SpiceDrivenPreferredChainConfig",
    "SpiceDrivenRobustnessConfig",
    "build_actual_spice_front_end_report",
    "build_common_inhibit_tuning_report",
    "build_preferred_chain_codesign_report",
    "build_preferred_chain_device_physicalization_report",
    "build_preferred_front_end_netlist_candidate_report",
    "build_preferred_physical_chain_report",
    "build_preferred_physical_chain_lc_report",
    "build_spice_driven_robustness_report",
    "build_spice_driven_preferred_chain_report",
    "build_chsh_result",
    "build_pre_click_comparison",
    "build_summary_metrics",
    "build_trial_energy_accounting",
    "build_physical_closure_drain_candidate_report",
    "build_physical_front_end_boundary_calibration_report",
    "build_physical_front_end_boundary_repro_check_report",
    "build_physical_front_end_boundary_diagnosis_report",
    "build_physical_front_end_candidate_report",
    "build_physical_front_end_four_branch_candidate_report",
    "build_physical_front_end_four_branch_refined_report",
    "build_physical_front_end_four_branch_resonant_report",
    "build_physical_front_end_handoff_report",
    "build_post_click_closure_report",
    "PRIOR_DIAGNOSIS_REFERENCE",
    "ReproCheckConfig",
    "aggregate_case_error",
    "benchmark_four_branch_physical_cases",
    "benchmark_refined_four_branch_cases",
    "benchmark_resonant_four_branch_cases",
    "classify_boundary_outcome",
    "classify_reproducibility",
    "closure_interpretations",
    "common_envelope_fidelity_metrics",
    "correlator_rms_error",
    "default_common_inhibit_tuning_sweep_config",
    "default_physical_closure_drain_config",
    "energy_preservation_metrics",
    "evaluate_tuned_closure_config",
    "finite_export_metrics",
    "fraction_error_metrics",
    "freeze_boundary_note_data",
    "materialize_candidate_trace",
    "preferred_common_mode_interpretation",
    "preferred_chain_codesign_benchmark_cases",
    "preferred_chain_device_physicalization_benchmark_cases",
    "preferred_front_end_netlist_benchmark_cases",
    "preferred_physical_chain_benchmark_cases",
    "preferred_physical_chain_lc_benchmark_cases",
    "spice_driven_preferred_chain_benchmark_cases",
    "spice_driven_robustness_points",
    "reduced_to_physical_mapping_summary",
    "run_actual_spice_front_end_benchmark",
    "run_actual_spice_front_end_case",
    "run_common_inhibit_parameter_sweeps",
    "run_four_branch_candidate_handoff",
    "run_four_branch_candidate_with_closure",
    "run_four_branch_candidate_with_physical_closure",
    "run_four_branch_physical_chsh",
    "run_four_branch_physical_handoff",
    "run_two_branch_physical_handoff",
    "run_preferred_physical_chain_benchmark",
    "run_preferred_physical_chain_candidate",
    "run_preferred_physical_chain_case",
    "run_preferred_chain_codesign_benchmark",
    "run_preferred_chain_codesign_candidate",
    "run_preferred_chain_codesign_case",
    "run_preferred_chain_device_physicalization_benchmark",
    "run_preferred_chain_device_physicalization_candidate",
    "run_preferred_chain_device_physicalization_case",
    "run_preferred_front_end_netlist_benchmark",
    "run_preferred_front_end_netlist_case",
    "run_preferred_physical_chain_lc_benchmark",
    "run_preferred_physical_chain_lc_candidate",
    "run_preferred_physical_chain_lc_case",
    "run_spice_driven_preferred_chain_benchmark",
    "run_spice_driven_preferred_chain_candidate",
    "run_spice_driven_preferred_chain_case",
    "run_spice_driven_robustness_sweep",
    "resolved_calibrated_boundary_config",
    "resolved_repro_check_config",
    "selected_handoff_export_config",
    "simulate_four_branch_candidate_pre_click_race",
    "simulate_explicit_lc_closure_drain",
    "simulate_codesigned_closure_drain",
    "simulate_actual_spice_front_end_candidate",
    "simulate_device_physicalized_closure_drain",
    "simulate_preferred_chain_device_physicalization_candidate",
    "simulate_preferred_chain_codesign_candidate",
    "simulate_preferred_front_end_netlist_candidate",
    "simulate_physical_closure_drain",
    "simulate_preferred_physical_chain_lc_candidate",
    "simulate_spice_driven_preferred_chain_candidate",
    "simulate_refined_four_branch_candidate",
    "simulate_resonant_four_branch_candidate",
    "simulate_post_click_closure",
    "summarize_energy_accounting_rows",
    "summarize_post_click_behavior",
    "tuned_physical_closure_drain_config",
    "simulate_four_branch_physical_candidate",
    "simulate_two_branch_physical_candidate",
]
