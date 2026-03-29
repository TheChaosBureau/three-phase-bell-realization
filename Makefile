PAPER = 30_bell_conservation_paper

DATE := $(shell date -u +%Y-%m-%d)
PYTHON ?= python
SIM_ARTIFACT_DIR ?= artifacts/sim/verification-run
SIM_AUDIT_DIR ?= artifacts/sim/verification-audit
TEST_ARTIFACT_DIR ?= artifacts/tests
ALLURE_RESULTS_DIR ?= $(TEST_ARTIFACT_DIR)/allure-results
ALLURE_REPORT_DIR ?= $(TEST_ARTIFACT_DIR)/allure-report

.PHONY: qmd ipynb pdf test

qmd:
	quarto convert paper/paper.ipynb -o qmd

ipynb:
	quarto convert paper/paper.qmd

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

test:
	@set +e; \
	mkdir -p "$(ALLURE_RESULTS_DIR)"; \
	poetry run pytest -vv --maxfail=0 --alluredir "$(ALLURE_RESULTS_DIR)" --clean-alluredir; \
	test_exit=$$?; \
	allure generate "$(ALLURE_RESULTS_DIR)" --clean --single-file -o "$(ALLURE_REPORT_DIR)"; \
	report_exit=$$?; \
	if [ $$test_exit -ne 0 ]; then exit $$test_exit; fi; \
	exit $$report_exit
