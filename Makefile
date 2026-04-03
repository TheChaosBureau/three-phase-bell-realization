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

.PHONY: qmd ipynb pdf pdf-all test test-pdf detector-search detector-next-report detector-integration-report latch-rig-report front-end-integration-report front-end-surrogate-report physical-front-end-candidate-report physical-front-end-handoff-report physical-front-end-boundary-diagnosis-report

qmd:
	quarto convert notebooks/20_clarke-surface.ipynb -o qmd

ipynb:
	quarto convert notebooks/20_clarke-surface.qmd

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

test-pdf: test
	mkdir -p "$(ALLURE_REPORT_DIR)"
	poetry run python scripts/allure_to_md.py \
		--results-dir "$(ALLURE_RESULTS_DIR)" \
		--out-path "$(ALLURE_REPORT_DIR)/$(ALLURE_MD_FILE)"
	quarto render "$(ALLURE_REPORT_DIR)/$(ALLURE_MD_FILE)" \
		--to pdf \
		--pdf-engine=tectonic

detector-search:
	mkdir -p "$(DETECTOR_OUTDIR)"
	poetry run $(PYTHON) -m detector_search.experiments.run_global_search "$(DETECTOR_MODEL)" \
		--samples "$(DETECTOR_SAMPLES)" \
		--jsonl "$(DETECTOR_JSONL)" \
		--csv "$(DETECTOR_CSV)" \
		--outdir "$(DETECTOR_OUTDIR)"

detector-next-report:
	mkdir -p "$(DETECTOR_NEXT_OUTDIR)"
	poetry run $(PYTHON) -m detector_search.experiments.run_next_steps_report \
		--outdir "$(DETECTOR_NEXT_OUTDIR)" \
		--samples-per-model "$(DETECTOR_NEXT_SAMPLES)" \
		--top-k "$(DETECTOR_NEXT_TOP_K)" \
		--grid-size "$(DETECTOR_NEXT_GRID)"

detector-integration-report:
	mkdir -p "$(DETECTOR_INTEGRATION_REPORT_OUTDIR)"
	poetry run $(PYTHON) -m detector_integration.experiments.run_summary_report \
		--outdir "$(DETECTOR_INTEGRATION_REPORT_OUTDIR)" \
		--detector-next-summary "$(DETECTOR_INTEGRATION_NEXT_SUMMARY)" \
		--two-branch-trials "$(DETECTOR_INTEGRATION_TWO_TRIALS)" \
		--four-branch-trials "$(DETECTOR_INTEGRATION_FOUR_TRIALS)"

latch-rig-report:
	mkdir -p "$(LATCH_RIG_OUTDIR)"
	poetry run $(PYTHON) -m detector_rig.latch_report \
		--outdir "$(LATCH_RIG_OUTDIR)"

front-end-integration-report:
	mkdir -p "$(FRONT_END_INTEGRATION_OUTDIR)"
	poetry run $(PYTHON) -m detector_integration.experiments.run_latch_enabled_summary_report \
		--outdir "$(FRONT_END_INTEGRATION_OUTDIR)" \
		--detector-next-summary "$(FRONT_END_INTEGRATION_NEXT_SUMMARY)" \
		--two-branch-trials "$(FRONT_END_INTEGRATION_TWO_TRIALS)" \
		--four-branch-trials "$(FRONT_END_INTEGRATION_FOUR_TRIALS)" \
		--mismatch-trials "$(FRONT_END_INTEGRATION_MISMATCH_TRIALS)"

front-end-surrogate-report:
	mkdir -p "$(FRONT_END_SURROGATE_OUTDIR)"
	poetry run $(PYTHON) -m front_end_surrogate.experiments.build_summary_report \
		--outdir "$(FRONT_END_SURROGATE_OUTDIR)" \
		--detector-next-summary "$(FRONT_END_SURROGATE_NEXT_SUMMARY)" \
		--two-branch-trials "$(FRONT_END_SURROGATE_TWO_TRIALS)" \
		--four-branch-trials "$(FRONT_END_SURROGATE_FOUR_TRIALS)"

physical-front-end-candidate-report:
	mkdir -p "$(PHYSICAL_FRONT_END_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_summary_report \
		--outdir "$(PHYSICAL_FRONT_END_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_TRIALS)"

physical-front-end-handoff-report:
	mkdir -p "$(PHYSICAL_FRONT_END_HANDOFF_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_handoff_report \
		--outdir "$(PHYSICAL_FRONT_END_HANDOFF_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_HANDOFF_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_HANDOFF_TRIALS)"

physical-front-end-boundary-diagnosis-report:
	mkdir -p "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_OUTDIR)"
	poetry run $(PYTHON) -m physical_front_end_candidate.experiments.build_boundary_diagnosis_report \
		--outdir "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_OUTDIR)" \
		--detector-next-summary "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_NEXT_SUMMARY)" \
		--trials "$(PHYSICAL_FRONT_END_BOUNDARY_DIAG_TRIALS)"
