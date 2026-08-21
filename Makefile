.PHONY: setup data warehouse dashboard report test check clean

PYTHON ?= python3

setup: data warehouse dashboard report

data:
	$(PYTHON) -m src.generate_data

warehouse: data
	$(PYTHON) -m src.build_warehouse

dashboard: warehouse
	$(PYTHON) -m src.export_dashboard

report: warehouse
	$(PYTHON) -m src.export_report

test:
	$(PYTHON) -m unittest discover -s tests -v

check: setup test

clean:
	$(PYTHON) -m src.clean
