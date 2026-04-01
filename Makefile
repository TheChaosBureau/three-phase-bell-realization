# PAPER = 30_bell_conservation_paper
PAPER = 20_clarke-surface

DATE := $(shell date -u +%Y-%m-%d)
PYTHON ?= python
TEST_ARTIFACT_DIR ?= artifacts/tests
ALLURE_RESULTS_DIR ?= $(TEST_ARTIFACT_DIR)/allure-results
ALLURE_REPORT_DIR ?= $(TEST_ARTIFACT_DIR)/allure-report
GIT_COMMIT_HASH ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
ALLURE_REPORT_FILE ?= index_$(GIT_COMMIT_HASH).html
ALLURE_MD_FILE ?= report_$(GIT_COMMIT_HASH).md
ALLURE_PDF_FILE ?= report_$(GIT_COMMIT_HASH).pdf

.PHONY: qmd ipynb pdf pdf-all test test-pdf 

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
