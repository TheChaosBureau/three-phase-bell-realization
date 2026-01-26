# ---------- Tunables ----------
PYTHON      ?= python
OUT_DIR     ?= runs_out
N_RUNS      ?= 300
FREQ        ?= 60
PPC         ?= 120
MAG         ?= 120
GEN_SEED    ?= 42

SETTINGS_SEED ?= 123
ALICE_OUT_DIR ?= alice_analysis
BOB_OUT_DIR   ?= bob_analysis
SUMMARY_OUT   ?= chsh_summary.csv

# CHSH angles (canonical defaults)
A_DEG       ?= 0
APRIME_DEG  ?= 45
B_DEG       ?= 22.5
BPRIME_DEG  ?= 67.5

# Optional generator previews
SAVE_PREVIEWS ?= 0
PLOT_DPI      ?= 140

# ---------- Files ----------
SETTINGS_CSV  := $(OUT_DIR)/settings.csv
ALICE_OUT     := $(ALICE_OUT_DIR)/alice_outcomes.csv
BOB_OUT       := $(BOB_OUT_DIR)/bob_outcomes.csv

# “existence” markers for directories
DIRS := $(OUT_DIR) $(ALICE_OUT_DIR) $(BOB_OUT_DIR)

# Glob lists (expanded at invocation time)
ALICE_RUNS := $(wildcard $(OUT_DIR)/alice_run*.csv)
BOB_RUNS   := $(wildcard $(OUT_DIR)/bob_run*.csv)

# ---------- Phony targets ----------
.PHONY: all generate settings analyze_alice analyze_bob aggregate clean help

all: aggregate
	@echo "Done. Summary: $(SUMMARY_OUT)"

help:
	@echo "Targets:"
	@echo "  make generate       # generate entangled pairs"
	@echo "  make settings       # generate settings.csv"
	@echo "  make analyze_alice  # analyze Alice's files"
	@echo "  make analyze_bob    # analyze Bob's files"
	@echo "  make aggregate      # compute CHSH E's and S"
	@echo "  make clean          # remove outputs"
	@echo ""
	@echo "Knobs (override like VAR=value):"
	@echo "  N_RUNS FREQ PPC MAG GEN_SEED SETTINGS_SEED"
	@echo "  A_DEG APRIME_DEG B_DEG BPRIME_DEG"
	@echo "  SAVE_PREVIEWS PLOT_DPI"
	@echo ""

# Ensure output dirs exist
$(DIRS):
	@mkdir -p $@

# ---------- Steps ----------
generate: $(OUT_DIR)
ifeq ($(SAVE_PREVIEWS),1)
	$(PYTHON) generate_pairs.py \
	  -n $(N_RUNS) -o $(OUT_DIR) --freq $(FREQ) --ppc $(PPC) --mag $(MAG) --seed $(GEN_SEED) \
	  --plot --plot-dpi $(PLOT_DPI)
else
	$(PYTHON) generate_pairs.py \
	  -n $(N_RUNS) -o $(OUT_DIR) --freq $(FREQ) --ppc $(PPC) --mag $(MAG) --seed $(GEN_SEED)
endif

settings: $(OUT_DIR)
	$(PYTHON) make_settings.py --runs $(N_RUNS) --out $(SETTINGS_CSV) --seed $(SETTINGS_SEED)

# Analyze Alice & Bob depend on runs + settings.
# Using wildcards means you should call `make generate settings` first,
# or just run `make all` which depends on these.
analyze_alice: $(ALICE_OUT_DIR) $(SETTINGS_CSV)
	$(PYTHON) chsh_analysis.py \
	  $(ALICE_RUNS) \
	  --role alice --settings $(SETTINGS_CSV) \
	  --a-deg $(A_DEG) --a-prime-deg $(APRIME_DEG) \
	  -o $(ALICE_OUT_DIR)

analyze_bob: $(BOB_OUT_DIR) $(SETTINGS_CSV)
	$(PYTHON) chsh_analysis.py \
	  $(BOB_RUNS) \
	  --role bob --settings $(SETTINGS_CSV) \
	  --b-deg $(B_DEG) --b-prime-deg $(BPRIME_DEG) \
	  -o $(BOB_OUT_DIR)

aggregate: generate settings analyze_alice analyze_bob
	$(PYTHON) chsh_aggregate.py \
	  --alice $(ALICE_OUT) \
	  --bob   $(BOB_OUT) \
	  --out   $(SUMMARY_OUT)

clean:
	@rm -rf $(OUT_DIR) $(ALICE_OUT_DIR) $(BOB_OUT_DIR) $(SUMMARY_OUT)
