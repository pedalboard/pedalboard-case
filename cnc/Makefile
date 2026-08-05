.DEFAULT_GOAL := help

install: ## Install dependencies
	pip install pyserial==3.5

test: ## Run probe-setup.py against mock machine simulator
	@python3 run_test.py

test-engrave: ## Run engrave-setup.py against mock machine simulator with crown
	@python3 run_test.py --engrave

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
