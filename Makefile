DATE := $(shell date -u +%Y-%m-%d)

qmd:
	quarto convert paper/paper.ipynb -o qmd

ipynb:
	quarto convert paper/paper.qmd

pdf:
	quarto render paper/paper.qmd \
		--to pdf \
		--execute \
		--no-execute-daemon \
		--no-cache \
		--pdf-engine=tectonic \
		--metadata date="$(DATE)"
