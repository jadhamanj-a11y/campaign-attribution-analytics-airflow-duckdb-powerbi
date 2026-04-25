setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

ingest:
	. .venv/bin/activate && python scripts/01_load_raw_to_duckdb.py

transform:
	. .venv/bin/activate && python scripts/02_run_sql_pipeline.py

export:
	. .venv/bin/activate && python scripts/03_export_outputs.py

dq:
	. .venv/bin/activate && python scripts/04_run_data_quality_checks.py

ml:
	. .venv/bin/activate && python scripts/05_run_ml_campaign_scoring.py
	. .venv/bin/activate && python scripts/06_export_ml_outputs.py

run:
	make ingest
	make transform
	make dq
	make export
	make ml
