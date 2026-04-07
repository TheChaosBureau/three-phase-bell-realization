# PAPER = 30_bell_conservation_paper
PAPER = 70_physical_model

DATE := $(shell date -u +%Y-%m-%d)
PYTHON ?= python
TEST_ARTIFACT_DIR ?= artifacts/tests
ALLURE_RESULTS_DIR ?= $(TEST_ARTIFACT_DIR)/allure-results
ALLURE_REPORT_DIR ?= $(TEST_ARTIFACT_DIR)/allure-report
GIT_COMMIT_HASH ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
ALLURE_REPORT_FILE ?= index_$(GIT_COMMIT_HASH).html
ALLURE_MD_FILE ?= report_$(GIT_COMMIT_HASH).md
ALLURE_PDF_FILE ?= report_$(GIT_COMMIT_HASH).pdf
DETECTOR_MODEL ?= shot_trigger
DETECTOR_SAMPLES ?= 20
DETECTOR_OUTDIR ?= artifacts/detector_search/$(DETECTOR_MODEL)
DETECTOR_JSONL ?= $(DETECTOR_OUTDIR)/results.jsonl
DETECTOR_CSV ?= $(DETECTOR_OUTDIR)/results.csv
DETECTOR_NEXT_OUTDIR ?= artifacts/detector_next
DETECTOR_NEXT_SAMPLES ?= 8
DETECTOR_NEXT_TOP_K ?= 5
DETECTOR_NEXT_GRID ?= 9
DETECTOR_INTEGRATION_REPORT_OUTDIR ?= artifacts/detector_integration/summary_report
DETECTOR_INTEGRATION_TWO_TRIALS ?= 4000
DETECTOR_INTEGRATION_FOUR_TRIALS ?= 6000
DETECTOR_INTEGRATION_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
LATCH_RIG_OUTDIR ?= artifacts/latch_rig
FRONT_END_INTEGRATION_OUTDIR ?= artifacts/front_end_integration
FRONT_END_INTEGRATION_TWO_TRIALS ?= 4000
FRONT_END_INTEGRATION_FOUR_TRIALS ?= 6000
FRONT_END_INTEGRATION_MISMATCH_TRIALS ?= 2000
FRONT_END_INTEGRATION_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
FRONT_END_SURROGATE_OUTDIR ?= artifacts/front_end_surrogate
FRONT_END_SURROGATE_TWO_TRIALS ?= 1000
FRONT_END_SURROGATE_FOUR_TRIALS ?= 1500
FRONT_END_SURROGATE_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_OUTDIR ?= artifacts/physical_front_end_candidate
PHYSICAL_FRONT_END_TRIALS ?= 1000
PHYSICAL_FRONT_END_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_HANDOFF_OUTDIR ?= artifacts/physical_front_end_handoff
PHYSICAL_FRONT_END_HANDOFF_TRIALS ?= 240
PHYSICAL_FRONT_END_HANDOFF_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_BOUNDARY_DIAG_OUTDIR ?= artifacts/physical_front_end_boundary_diagnosis
PHYSICAL_FRONT_END_BOUNDARY_DIAG_TRIALS ?= 120
PHYSICAL_FRONT_END_BOUNDARY_DIAG_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_BOUNDARY_CAL_OUTDIR ?= artifacts/physical_front_end_boundary_calibration
PHYSICAL_FRONT_END_BOUNDARY_CAL_TRIALS ?= 120
PHYSICAL_FRONT_END_BOUNDARY_CAL_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_BOUNDARY_REPRO_OUTDIR ?= artifacts/physical_front_end_boundary_repro_check
PHYSICAL_FRONT_END_BOUNDARY_REPRO_MIN_TRIALS ?= 500
PHYSICAL_FRONT_END_BOUNDARY_REPRO_TARGET_DECISIVE ?= 100
PHYSICAL_FRONT_END_BOUNDARY_REPRO_MAX_TRIALS ?= 20000
PHYSICAL_FRONT_END_BOUNDARY_REPRO_BATCH_TRIALS ?= 500
PHYSICAL_FRONT_END_BOUNDARY_REPRO_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_FOUR_BRANCH_OUTDIR ?= artifacts/physical_front_end_four_branch_candidate
PHYSICAL_FRONT_END_FOUR_BRANCH_TRIALS ?= 4000
PHYSICAL_FRONT_END_FOUR_BRANCH_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_OUTDIR ?= artifacts/physical_front_end_four_branch_refined
PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_TRIALS ?= 4000
PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_OUTDIR ?= artifacts/physical_front_end_four_branch_resonant
PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_TRIALS ?= 4000
PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
POST_CLICK_CLOSURE_OUTDIR ?= artifacts/post_click_closure_spec
POST_CLICK_CLOSURE_TRIALS ?= 200
POST_CLICK_CLOSURE_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_CLOSURE_DRAIN_OUTDIR ?= artifacts/physical_closure_drain_candidate
PHYSICAL_CLOSURE_DRAIN_TRIALS ?= 200
PHYSICAL_CLOSURE_DRAIN_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PHYSICAL_CLOSURE_DRAIN_TUNING_OUTDIR ?= artifacts/physical_closure_drain_tuning
PHYSICAL_CLOSURE_DRAIN_TUNING_TRIALS ?= 200
PHYSICAL_CLOSURE_DRAIN_TUNING_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PREFERRED_PHYSICAL_CHAIN_OUTDIR ?= artifacts/preferred_physical_chain
PREFERRED_PHYSICAL_CHAIN_TRIALS ?= 1200
PREFERRED_PHYSICAL_CHAIN_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PREFERRED_PHYSICAL_CHAIN_LC_OUTDIR ?= artifacts/preferred_physical_chain_lc
PREFERRED_PHYSICAL_CHAIN_LC_TRIALS ?= 1200
PREFERRED_PHYSICAL_CHAIN_LC_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PREFERRED_FRONT_END_NETLIST_OUTDIR ?= artifacts/preferred_front_end_netlist_candidate
PREFERRED_FRONT_END_NETLIST_TRIALS ?= 1200
PREFERRED_FRONT_END_NETLIST_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PREFERRED_CHAIN_CODESIGN_OUTDIR ?= artifacts/preferred_chain_codesign
PREFERRED_CHAIN_CODESIGN_TRIALS ?= 1200
PREFERRED_CHAIN_CODESIGN_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_OUTDIR ?= artifacts/preferred_chain_device_physicalization
PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_TRIALS ?= 1200
PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
ACTUAL_SPICE_FRONT_END_OUTDIR ?= artifacts/actual_spice_front_end
SPICE_DRIVEN_PREFERRED_CHAIN_OUTDIR ?= artifacts/spice_driven_preferred_chain
SPICE_DRIVEN_PREFERRED_CHAIN_TRIALS ?= 1200
SPICE_DRIVEN_PREFERRED_CHAIN_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv
SPICE_DRIVEN_ROBUSTNESS_OUTDIR ?= artifacts/spice_driven_robustness
SPICE_DRIVEN_ROBUSTNESS_TRIALS ?= 180
SPICE_DRIVEN_ROBUSTNESS_NEXT_SUMMARY ?= artifacts/detector_next/results_summary.csv

.PHONY: qmd ipynb pdf pdf-all test test-pdf detector-search detector-next-report detector-integration-report latch-rig-report front-end-integration-report front-end-surrogate-report physical-front-end-candidate-report physical-front-end-handoff-report physical-front-end-boundary-diagnosis-report physical-front-end-boundary-calibration-report physical-front-end-boundary-repro-check-report physical-front-end-four-branch-candidate-report physical-front-end-four-branch-refined-report physical-front-end-four-branch-resonant-report post-click-closure-spec-report physical-closure-drain-candidate-report physical-closure-drain-tuning-report physical-closure-drain-tuning-refresh-summary preferred-physical-chain-report preferred-physical-chain-lc-report preferred-front-end-netlist-candidate-report preferred-chain-codesign-report preferred-chain-device-physicalization-report actual-spice-front-end-report spice-driven-preferred-chain-report spice-driven-robustness-report

qmd:
	quarto convert notebooks/20_clarke-surface.ipynb -o qmd
	@printf '\a'

ipynb:
	quarto convert notebooks/20_clarke-surface.qmd
	@printf '\a'

pdf:
	QUARTO_PYTHON=.venv/bin/python quarto render notebooks/$(PAPER).qmd \
		--to pdf \
		--execute \
		--no-execute-daemon \
		--no-cache \
		--pdf-engine=tectonic \
		--metadata date="$(DATE)"
	mkdir -p artifacts/paper
	mv notebooks/$(PAPER).pdf artifacts/paper/$(PAPER).pdf
	@printf '\a'

pdf-all:
	@mkdir -p artifacts/paper
	@set -e; \
	for f in notebooks/*.md notebooks/*.qmd; do \
		[ -e "$$f" ] || continue; \
		QUARTO_PYTHON=.venv/bin/python quarto render "$$f" \
			--to pdf \
			--execute \
			--no-execute-daemon \
			--no-cache \
			--pdf-engine=tectonic \
			--metadata date="$(DATE)"; \
		pdf="$${f%.*}.pdf"; \
		mv "$$pdf" "artifacts/paper/$$(basename "$$pdf")"; \
	done
	@printf '\a'

test:
	@set +e; \
	mkdir -p "$(ALLURE_RESULTS_DIR)"; \
	poetry run pytest -vv --maxfail=0 --alluredir "$(ALLURE_RESULTS_DIR)" --clean-alluredir; \
	test_exit=$$?; \
	allure generate "$(ALLURE_RESULTS_DIR)" --clean --single-file -o "$(ALLURE_REPORT_DIR)"; \
	report_exit=$$?; \
	if [ $$report_exit -eq 0 ] && [ -f "$(ALLURE_REPORT_DIR)/index.html" ]; then mv "$(ALLURE_REPORT_DIR)/index.html" "$(ALLURE_REPORT_DIR)/$(ALLURE_REPORT_FILE)"; fi; \
	if [ $$test_exit -ne 0 ]; then exit $$test_exit; fi; \
	exit $$report_exit
	@printf '\a'

test-pdf: test
	mkdir -p "$(ALLURE_REPORT_DIR)"
	poetry run python scripts/allure_to_md.py \
		--results-dir "$(ALLURE_RESULTS_DIR)" \
		--out-path "$(ALLURE_REPORT_DIR)/$(ALLURE_MD_FILE)"
	quarto render "$(ALLURE_REPORT_DIR)/$(ALLURE_MD_FILE)" \
		--to pdf \
		--pdf-engine=tectonic
	@printf '\a'

detector-search:
	mkdir -p "$(DETECTOR_OUTDIR)"
	poetry run $(PYTHON) -m detector_search.experiments.run_global_search "$(DETECTOR_MODEL)" \
		--samples "$(DETECTOR_SAMPLES)" \
		--jsonl "$(DETECTOR_JSONL)" \
		--csv "$(DETECTOR_CSV)" \
		--outdir "$(DETECTOR_OUTDIR)"
	@printf '\a'

detector-next-report:
	mkdir -p "$(DETECTOR_NEXT_OUTDIR)"
	poetry run $(PYTHON) -m detector_search.experiments.run_next_steps_report \
		--outdir "$(DETECTOR_NEXT_OUTDIR)" \
		--samples-per-model "$(DETECTOR_NEXT_SAMPLES)" \
		--top-k "$(DETECTOR_NEXT_TOP_K)" \
		--grid-size "$(DETECTOR_NEXT_GRID)"
	@printf '\a'

detector-integration-report:
	mkdir -p "$(DETECTOR_INTEGRATION_REPORT_OUTDIR)"
	poetry run $(PYTHON) -m detector_integration.experiments.run_summary_report \
		--outdir "$(DETECTOR_INTEGRATION_REPORT_OUTDIR)" \
		--detector-next-summary "$(DETECTOR_INTEGRATION_NEXT_SUMMARY)" \
		--two-branch-trials "$(DETECTOR_INTEGRATION_TWO_TRIALS)" \
		--four-branch-trials "$(DETECTOR_INTEGRATION_FOUR_TRIALS)"
	@printf '\a'

latch-rig-report:
	mkdir -p "$(LATCH_RIG_OUTDIR)"
	poetry run $(PYTHON) -m detector_rig.latch_report \
		--outdir "$(LATCH_RIG_OUTDIR)"
	@printf '\a'

front-end-integration-report:
	mkdir -p "$(FRONT_END_INTEGRATION_OUTDIR)"
	poetry run $(PYTHON) -m detector_integration.experiments.run_latch_enabled_summary_report \
		--outdir "$(FRONT_END_INTEGRATION_OUTDIR)" \
		--detector-next-summary "$(FRONT_END_INTEGRATION_NEXT_SUMMARY)" \
		--two-branch-trials "$(FRONT_END_INTEGRATION_TWO_TRIALS)" \
		--four-branch-trials "$(FRONT_END_INTEGRATION_FOUR_TRIALS)" \
		--mismatch-trials "$(FRONT_END_INTEGRATION_MISMATCH_TRIALS)"
	@printf '\a'

front-end-surrogate-report:
	mkdir -p "$(FRONT_END_SURROGATE_OUTDIR)"
	poetry run $(PYTHON) -m front_end_surrogate.experiments.build_summary_report \
		--outdir "$(FRONT_END_SURROGATE_OUTDIR)" \
		--detector-next-summary "$(FRONT_END_SURROGATE_NEXT_SUMMARY)" \
		--two-branch-trials "$(FRONT_END_SURROGATE_TWO_TRIALS)" \
		--four-branch-trials "$(FRONT_END_SURROGATE_FOUR_TRIALS)"
	@printf '\a'

physical-front-end-candidate-report:
	mkdir -p "$(PHYSICAL_FRONT_END_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_summary_report \
		--outdir "$(PHYSICAL_FRONT_END_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_TRIALS)"
	@printf '\a'

physical-front-end-handoff-report:
	mkdir -p "$(PHYSICAL_FRONT_END_HANDOFF_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_handoff_report \
		--outdir "$(PHYSICAL_FRONT_END_HANDOFF_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_HANDOFF_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_HANDOFF_TRIALS)"
	@printf '\a'

physical-front-end-boundary-diagnosis-report:
	mkdir -p "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_boundary_diagnosis_report \
		--outdir "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_TRIALS)"
	@printf '\a'

physical-front-end-boundary-calibration-report:
	mkdir -p "$(PHYSICAL_FRONT_END_BOUNDARY_CAL_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_boundary_calibration_report \
		--outdir "$(PHYSICAL_FRONT_END_BOUNDARY_CAL_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_BOUNDARY_CAL_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_BOUNDARY_CAL_TRIALS)"
	@printf '\a'

physical-front-end-boundary-repro-check-report:
	mkdir -p "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_boundary_repro_check_report \
		--outdir "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_NEXT_SUMMARY)" \
		--min-trials-per-case "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_MIN_TRIALS)" \
		--target-decisive-count "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_TARGET_DECISIVE)" \
		--max-trials-per-case "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_MAX_TRIALS)" \
		--batch-trials "$(PHYSICAL_FRONT_END_BOUNDARY_REPRO_BATCH_TRIALS)"
	@printf '\a'

physical-front-end-four-branch-candidate-report:
	mkdir -p "$(PHYSICAL_FRONT_END_FOUR_BRANCH_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_four_branch_candidate_report \
		--outdir "$(PHYSICAL_FRONT_END_FOUR_BRANCH_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_FOUR_BRANCH_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_FOUR_BRANCH_TRIALS)"
	@printf '\a'

physical-front-end-four-branch-refined-report:
	mkdir -p "$(PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_four_branch_refined_report \
		--outdir "$(PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_FOUR_BRANCH_REFINED_TRIALS)"
	@printf '\a'

physical-front-end-four-branch-resonant-report:
	mkdir -p "$(PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_four_branch_resonant_report \
		--outdir "$(PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_FOUR_BRANCH_RESONANT_TRIALS)"
	@printf '\a'

post-click-closure-spec-report:
	mkdir -p "$(POST_CLICK_CLOSURE_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_post_click_closure_report \
		--outdir "$(POST_CLICK_CLOSURE_OUTDIR)" \
		--detector-next-summary "$(POST_CLICK_CLOSURE_NEXT_SUMMARY)" \
		--trials "$(POST_CLICK_CLOSURE_TRIALS)"
	@printf '\a'

physical-closure-drain-candidate-report:
	mkdir -p "$(PHYSICAL_CLOSURE_DRAIN_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_physical_closure_drain_candidate_report \
		--outdir "$(PHYSICAL_CLOSURE_DRAIN_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_CLOSURE_DRAIN_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_CLOSURE_DRAIN_TRIALS)"
	@printf '\a'

physical-closure-drain-tuning-report:
	mkdir -p "$(PHYSICAL_CLOSURE_DRAIN_TUNING_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_common_inhibit_tuning_report \
		--outdir "$(PHYSICAL_CLOSURE_DRAIN_TUNING_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_CLOSURE_DRAIN_TUNING_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_CLOSURE_DRAIN_TUNING_TRIALS)"
	@printf '\a'

physical-closure-drain-tuning-refresh-summary:
	mkdir -p "$(PHYSICAL_CLOSURE_DRAIN_TUNING_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.refresh_common_inhibit_tuning_summary \
		--outdir "$(PHYSICAL_CLOSURE_DRAIN_TUNING_OUTDIR)"
	@printf '\a'

preferred-physical-chain-report:
	mkdir -p "$(PREFERRED_PHYSICAL_CHAIN_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_preferred_physical_chain_report \
		--outdir "$(PREFERRED_PHYSICAL_CHAIN_OUTDIR)" \
		--detector-next-summary-csv "$(PREFERRED_PHYSICAL_CHAIN_NEXT_SUMMARY)" \
		--n-trials "$(PREFERRED_PHYSICAL_CHAIN_TRIALS)"
	@printf '\a'

preferred-physical-chain-lc-report:
	mkdir -p "$(PREFERRED_PHYSICAL_CHAIN_LC_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_preferred_physical_chain_lc_report \
		--outdir "$(PREFERRED_PHYSICAL_CHAIN_LC_OUTDIR)" \
		--detector-next-summary-csv "$(PREFERRED_PHYSICAL_CHAIN_LC_NEXT_SUMMARY)" \
		--n-trials "$(PREFERRED_PHYSICAL_CHAIN_LC_TRIALS)"
	@printf '\a'

preferred-front-end-netlist-candidate-report:
	mkdir -p "$(PREFERRED_FRONT_END_NETLIST_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_preferred_front_end_netlist_candidate_report \
		--outdir "$(PREFERRED_FRONT_END_NETLIST_OUTDIR)" \
		--detector-next-summary-csv "$(PREFERRED_FRONT_END_NETLIST_NEXT_SUMMARY)" \
		--n-trials "$(PREFERRED_FRONT_END_NETLIST_TRIALS)"
	@printf '\a'

preferred-chain-codesign-report:
	mkdir -p "$(PREFERRED_CHAIN_CODESIGN_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_preferred_chain_codesign_report \
		--outdir "$(PREFERRED_CHAIN_CODESIGN_OUTDIR)" \
		--detector-next-summary-csv "$(PREFERRED_CHAIN_CODESIGN_NEXT_SUMMARY)" \
		--n-trials "$(PREFERRED_CHAIN_CODESIGN_TRIALS)"
	@printf '\a'

preferred-chain-device-physicalization-report:
	mkdir -p "$(PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_preferred_chain_device_physicalization_report \
		--outdir "$(PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_OUTDIR)" \
		--detector-next-summary-csv "$(PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_NEXT_SUMMARY)" \
		--n-trials "$(PREFERRED_CHAIN_DEVICE_PHYSICALIZATION_TRIALS)"
	@printf '\a'

actual-spice-front-end-report:
	mkdir -p "$(ACTUAL_SPICE_FRONT_END_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_actual_spice_front_end_report \
		--outdir "$(ACTUAL_SPICE_FRONT_END_OUTDIR)"
	@printf '\a'

spice-driven-preferred-chain-report:
	mkdir -p "$(SPICE_DRIVEN_PREFERRED_CHAIN_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_spice_driven_preferred_chain_report \
		--outdir "$(SPICE_DRIVEN_PREFERRED_CHAIN_OUTDIR)" \
		--detector-next-summary-csv "$(SPICE_DRIVEN_PREFERRED_CHAIN_NEXT_SUMMARY)" \
		--n-trials "$(SPICE_DRIVEN_PREFERRED_CHAIN_TRIALS)"
	@printf '\a'

spice-driven-robustness-report:
	mkdir -p "$(SPICE_DRIVEN_ROBUSTNESS_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_spice_driven_robustness_report \
		--outdir "$(SPICE_DRIVEN_ROBUSTNESS_OUTDIR)" \
		--detector-next-summary-csv "$(SPICE_DRIVEN_ROBUSTNESS_NEXT_SUMMARY)" \
		--n-trials "$(SPICE_DRIVEN_ROBUSTNESS_TRIALS)"
	@printf '\a'
