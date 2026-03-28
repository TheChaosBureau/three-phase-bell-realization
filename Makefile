DATE := $(shell date -u +%Y-%m-%d)
PYTHON ?= python
SIM_ARTIFACT_DIR ?= artifacts/sim/verification-run
SIM_AUDIT_DIR ?= artifacts/sim/verification-audit

.PHONY: qmd ipynb pdf verification-run verification-audit verification

qmd:
	quarto convert paper/paper.ipynb -o qmd

ipynb:
	quarto convert paper/paper.qmd

pdf:
	QUARTO_PYTHON=.venv/bin/python quarto render paper/chsh/paper.qmd \
		--to pdf \
		--execute \
		--no-execute-daemon \
		--no-cache \
		--pdf-engine=tectonic \
		--metadata date="$(DATE)"

verification-run:
	$(PYTHON) scripts/run_sweeps.py --preset risk_first_full --artifact-dir $(SIM_ARTIFACT_DIR)
	$(PYTHON) scripts/analyze_results.py $(SIM_ARTIFACT_DIR)

verification-audit:
	$(PYTHON) scripts/build_verification_audit.py $(SIM_ARTIFACT_DIR) --output-dir $(SIM_AUDIT_DIR)

verification: verification-run verification-audit
