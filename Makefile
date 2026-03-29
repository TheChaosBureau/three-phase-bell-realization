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

tests:
	# todo: also build single-file allure report, regardless of test suite pass / fail (also don't stop tests if one fails)
	poetry run pytest -vv