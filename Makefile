.PHONY: install dev-install lint test clean run-example

install:
	pip install .

dev-install:
	pip install -e ".[dev]"

lint:
	ruff check src tests configs

test:
	pytest tests/

clean:
	rm -rf build dist src/*.egg-info .pytest_cache .ruff_cache

run-example:
	python -m autosilix.cli run --config configs/designs/sequence_detector.yaml --mock
