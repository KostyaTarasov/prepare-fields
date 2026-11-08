.DEFAULT_GOAL := help
INPUT ?= examples/products.json
FORMAT ?= md

help:
	@echo "make run [INPUT=examples/products.json] [FORMAT=md|json] - собрать карточки"
	@echo "make test                                                - тесты"
	@echo "make lint                                                - линтер и форматирование"

run:
	uv run prepare-fields $(INPUT) --format $(FORMAT)

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

.PHONY: help run test lint
