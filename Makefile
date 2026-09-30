PYTHON ?= python

.PHONY: install check test lint format audit run migrate collectstatic

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

check:
	$(PYTHON) manage.py check
	$(PYTHON) manage.py makemigrations --check --dry-run

test:
	$(PYTHON) -m coverage run manage.py test --settings=config.test_settings
	$(PYTHON) -m coverage report

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

audit:
	$(PYTHON) -m pip_audit -r requirements.txt

run:
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py migrate

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput
