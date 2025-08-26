.PHONY: setup fmt lint typecheck test run

setup:
	python -m venv venv
	./venv/bin/python -m pip install --upgrade pip
	./venv/bin/pip install -e .[dev]

fmt:
	ruff format .

lint:
	ruff check .

typecheck:
	mypy gazedeck

test:
	pytest -q

run:
	./venv/bin/python -m gazedeck.runners.single_process \
		--screen-w 1920 \
		--screen-h 1080 \
		--markers-json config/markers/screen_4tags.example.json \
		--tag-rate auto \
		--ws-port 8765 \
		--homography-mode every
