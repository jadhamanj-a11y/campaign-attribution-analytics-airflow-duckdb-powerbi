from datetime import datetime, timedelta
from pathlib import Path
import subprocess

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


PROJECT_ROOT = Path("/home/jadha/projects/campaign-attribution-analytics-airflow-duckdb-powerbi")


default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "email_on_failure": False,
    "email_on_retry": False,
}


def run_command(command: str):
    result = subprocess.run(
        command,
        shell=True,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    print("STDOUT:")
    print(result.stdout)

    print("STDERR:")
    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}")


def load_raw_to_duckdb():
    run_command(". .venv/bin/activate && python scripts/01_load_raw_to_duckdb.py")


def run_sql_transformations():
    run_command(". .venv/bin/activate && python scripts/02_run_sql_pipeline.py")


def run_data_quality_checks():
    run_command(". .venv/bin/activate && python scripts/04_run_data_quality_checks.py")


def export_business_outputs():
    run_command(". .venv/bin/activate && python scripts/03_export_outputs.py")


def run_ml_campaign_scoring():
    run_command(". .venv/bin/activate && python scripts/05_run_ml_campaign_scoring.py")


def export_ml_outputs():
    run_command(". .venv/bin/activate && python scripts/06_export_ml_outputs.py")


with DAG(
    dag_id="campaign_effectiveness_attribution_pipeline",
    description="Campaign attribution, coincidental lift analysis, DQ, ML scoring, and BI output pipeline",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["campaign", "attribution", "duckdb", "airflow", "powerbi", "ml"],
) as dag:

    start = EmptyOperator(task_id="start")

    task_load_raw = PythonOperator(
        task_id="load_raw_to_duckdb",
        python_callable=load_raw_to_duckdb,
    )

    task_transform = PythonOperator(
        task_id="run_sql_transformations",
        python_callable=run_sql_transformations,
    )

    task_dq = PythonOperator(
        task_id="run_data_quality_checks",
        python_callable=run_data_quality_checks,
    )

    task_export_business = PythonOperator(
        task_id="export_odec_and_powerbi_outputs",
        python_callable=export_business_outputs,
    )

    task_ml = PythonOperator(
        task_id="run_ml_campaign_response_scoring",
        python_callable=run_ml_campaign_scoring,
    )

    task_export_ml = PythonOperator(
        task_id="export_ml_powerbi_outputs",
        python_callable=export_ml_outputs,
    )

    end = EmptyOperator(task_id="end")

    (
        start
        >> task_load_raw
        >> task_transform
        >> task_dq
        >> task_export_business
        >> task_ml
        >> task_export_ml
        >> end
    )
