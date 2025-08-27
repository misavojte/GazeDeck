.PHONY: setup fmt lint typecheck test run

# Detect platform and set virtual environment paths
ifeq ($(OS),Windows_NT)
	VENV_PYTHON = ./.venv/Scripts/python.exe
	VENV_PIP = ./.venv/Scripts/pip.exe
else
	VENV_PYTHON = ./.venv/bin/python
	VENV_PIP = ./.venv/bin/pip
endif

setup:
	python -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e .[dev]

fmt:
	ruff format .

lint:
	ruff check .

typecheck:
	mypy gazedeck

test:
	pytest -q

run:
	$(VENV_PYTHON) -m gazedeck.runners.single_process \
		--screen-w 1080 \
		--screen-h 720 \
		--markers-json gazedeck/config/markers/base/config.json \
		--tag-rate auto \
		--ws-port 8765 \
		--homography-mode every
