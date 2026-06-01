.PHONY: install run lint format typecheck test coverage evaluate precommit migrate migrate-create

install:
	python -m pip install --upgrade pip
	pip install -e .[dev]
	pre-commit install

run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

lint:
	ruff check .

format:
	ruff format .
	ruff check . --fix

typecheck:
	mypy app

test:
	pytest -q

coverage:
	pytest --cov=app --cov-report=xml --cov-report=html --cov-report=term

evaluate:
	python scripts/evaluate_retrieval.py --output-json

precommit:
	pre-commit run --all-files

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"
