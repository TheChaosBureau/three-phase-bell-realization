DATE := $(shell date -u +%Y-%m-%d)

qmd:
	quarto convert paper/paper.ipynb --to qmd

pdf:
	quarto render paper/paper.qmd \
		--to pdf \
		--execute \
		--no-execute-daemon \
		--no-cache \
		--pdf-engine=tectonic \
		--metadata date="$(DATE)"
