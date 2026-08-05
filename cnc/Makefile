PYTHON     := python3
PLATES_DIR := $(abspath ../../../laenzlinger/plates)
PLATES_PY  := $(PLATES_DIR)/.venv/bin/python3
PIP        := $(PLATES_PY) -m pip

.DEFAULT_GOAL := help

install: ## Install dependencies into plates venv
	@test -f "$(PLATES_PY)" || (echo "ERROR: plates venv not found at $(PLATES_DIR)/.venv" \
	  && echo "Run: cd $(PLATES_DIR) && mise install && make install" && exit 1)
	$(PIP) install pyserial==3.5
	$(PIP) install -e "$(PLATES_DIR)"
	@echo "Done. Run scripts with: $(PLATES_PY)"

test: ## Run probe-setup.py against mock machine simulator
	@$(PLATES_PY) run_test.py

test-engrave: ## Run engrave-setup.py against simulator with 0.3mm crown
	@$(PLATES_PY) run_test.py --engrave

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install test test-engrave help
