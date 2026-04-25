import sys
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

from qa_config import (
    RAW_DIR,
    DB_PATH,
    REQUIRED_RAW_FILES,
    MIN_ROW_COUNTS,
    EXPECTED_SCHEMAS,
)


qa_results = []


def add_result(check_name, status, details):
    qa_results.append(
        {
            "check_name": check_name,
            "status": status,
            "details": details,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


def fail_fast_if_needed():
    failed = [r for r in qa_results if r["status"] == "FAILED"]
    if failed:
        report = pd.DataFrame(qa_results)
        report_path = Path("qa/reports/qa_report.csv")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(report_path, index=False)

        print("\nQA FAILED")
        print(report.to_string(index=False))
        print(f"\nReport written to: {report_path}")
        sys.exit(1)


def run_file_level_qa():
    print("Running file-level QA...")

    for file_name in REQUIRED_RAW_FILES:
        file_path = RAW_DIR / file_name

        if not file_path.exists():
            add_result(
                f"File exists: {file_name}",
                "FAILED",
                f"Missing required file: {file_path}",
            )
            continue

        if file_path.stat().st_size == 0:
            add_result(
                f"File not empty: {file_name}",
                "FAILED",
                f"File is empty: {file_path}",
            )
        else:
            add_result(
                f"File not empty: {file_name}",
                "PASSED",
                f"File exists and size={file_path.stat().st_size} bytes",
            )


def run_schema_qa():
    print("Running schema QA...")

    for file_name, expected_cols in EXPECTED_SCHEMAS.items():
        file_path = RAW_DIR / file_name

        if not file_path.exists():
            add_result(
                f"Schema check: {file_name}",
                "FAILED",
                "File missing, schema cannot be validated",
            )
            continue

        df = pd.read_csv(file_path)
        actual_cols = set(df.columns)
        expected_col_set = set(expected_cols.keys())

        missing_cols = expected_col_set - actual_cols
        extra_cols = actual_cols - expected_col_set

        if missing_cols:
            add_result(
                f"Schema columns: {file_name}",
                "FAILED",
                f"Missing columns: {sorted(missing_cols)}",
            )
        else:
            add_result(
                f"Schema columns: {file_name}",
                "PASSED",
                "All required columns exist",
            )

        if extra_cols:
            add_result(
                f"Extra columns: {file_name}",
                "WARNING",
                f"Extra columns found: {sorted(extra_cols)}",
            )
        else:
            add_result(
                f"Extra columns: {file_name}",
                "PASSED",
                "No unexpected columns",
            )

        for col, expected_type in expected_cols.items():
            if col not in df.columns:
                continue

            if expected_type == "number":
                is_numeric = pd.api.types.is_numeric_dtype(df[col])
                if is_numeric:
                    add_result(
                        f"Column type: {file_name}.{col}",
                        "PASSED",
                        "Numeric column validated",
                    )
                else:
                    converted = pd.to_numeric(df[col], errors="coerce")
                    invalid_count = converted.isna().sum() - df[col].isna().sum()

                    if invalid_count > 0:
                        add_result(
                            f"Column type: {file_name}.{col}",
                            "FAILED",
                            f"Expected numeric, invalid values={invalid_count}",
                        )
                    else:
                        add_result(
                            f"Column type: {file_name}.{col}",
                            "PASSED",
                            "Numeric-compatible column validated",
                        )
            else:
                add_result(
                    f"Column type: {file_name}.{col}",
                    "PASSED",
                    "String/object-compatible column validated",
                )


def run_raw_row_count_qa():
    print("Running raw row-count QA...")

    for file_name, min_count in MIN_ROW_COUNTS.items():
        file_path = RAW_DIR / file_name

        if not file_path.exists():
            add_result(
                f"Raw row count: {file_name}",
                "FAILED",
                "File missing",
            )
            continue

        df = pd.read_csv(file_path)
        row_count = len(df)

        if row_count < min_count:
            add_result(
                f"Raw row count: {file_name}",
                "FAILED",
                f"Expected at least {min_count}, actual={row_count}",
            )
        else:
            add_result(
                f"Raw row count: {file_name}",
                "PASSED",
                f"Actual rows={row_count}",
            )



def normalize_table_name(table_name):
    """
    Supports both:
    - table_name
    - schema_name.table_name
    """
    if "." in table_name:
        schema_name, pure_table_name = table_name.split(".", 1)
        return schema_name, pure_table_name
    return None, table_name


def table_exists(con, table_name):
    schema_name, pure_table_name = normalize_table_name(table_name)

    if schema_name:
        result = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = ?
              AND table_name = ?
            """,
            [schema_name, pure_table_name],
        ).fetchone()[0]
    else:
        result = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?
            """,
            [pure_table_name],
        ).fetchone()[0]

    return result > 0

def run_duckdb_table_qa():
    print("Running DuckDB table QA...")

    if not DB_PATH.exists():
        add_result(
            "DuckDB database exists",
            "FAILED",
            f"DuckDB file missing: {DB_PATH}",
        )
        return

    add_result(
        "DuckDB database exists",
        "PASSED",
        f"DuckDB file found: {DB_PATH}",
    )

    con = duckdb.connect(str(DB_PATH))

    expected_tables = [
        "raw.campaign_master",
        "raw.grp_spots",
        "raw.odec_mapping",
        "raw.sessions",
        "staging.stg_campaign_master",
        "staging.stg_grp_spots",
        "staging.stg_odec_mapping",
        "staging.stg_sessions",
        "intermediate.int_session_campaign_candidates",
        "intermediate.int_attributed_sessions",
        "intermediate.int_pre_post_spot_sessions",
        "marts.fact_campaign_sessions",
        "marts.mart_campaign_effectiveness",
        "marts.odec_ready_campaign_dataset",
        "marts.ml_campaign_response_scores",
        "metadata.dq_results",
        "metadata.ingestion_log",
    ]

    for table in expected_tables:
        if table_exists(con, table):
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            add_result(
                f"DuckDB table exists: {table}",
                "PASSED",
                f"Rows={count}",
            )
        else:
            add_result(
                f"DuckDB table exists: {table}",
                "FAILED",
                "Table missing",
            )

    con.close()


def run_null_duplicate_qa():
    print("Running null and duplicate QA...")

    if not DB_PATH.exists():
        add_result(
            "Null duplicate QA",
            "FAILED",
            "DuckDB database missing",
        )
        return

    con = duckdb.connect(str(DB_PATH))

    checks = [
        ("raw.campaign_master", "campaign_id"),
        ("raw.grp_spots", "spot_id"),
        ("raw.sessions", "session_id"),
        ("raw.odec_mapping", "channel_id"),
    ]

    for table, key_col in checks:
        if not table_exists(con, table):
            add_result(
                f"Null check: {table}.{key_col}",
                "FAILED",
                "Table missing",
            )
            continue

        null_count = con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {key_col} IS NULL"
        ).fetchone()[0]

        duplicate_count = con.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT {key_col}, COUNT(*) AS cnt
                FROM {table}
                GROUP BY {key_col}
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        if null_count > 0:
            add_result(
                f"Null check: {table}.{key_col}",
                "FAILED",
                f"Null count={null_count}",
            )
        else:
            add_result(
                f"Null check: {table}.{key_col}",
                "PASSED",
                "No null primary keys",
            )

        if duplicate_count > 0:
            add_result(
                f"Duplicate check: {table}.{key_col}",
                "FAILED",
                f"Duplicate key groups={duplicate_count}",
            )
        else:
            add_result(
                f"Duplicate check: {table}.{key_col}",
                "PASSED",
                "No duplicate primary keys",
            )

    con.close()


def run_attribution_window_qa():
    print("Running attribution-window QA...")

    if not DB_PATH.exists():
        add_result(
            "Attribution-window QA",
            "FAILED",
            "DuckDB database missing",
        )
        return

    con = duckdb.connect(str(DB_PATH))

    possible_tables = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        """
    ).fetchdf()["table_name"].tolist()

    attribution_table_candidates = [
        "intermediate.int_attributed_sessions",
        "marts.fact_campaign_sessions",
        "marts.mart_campaign_effectiveness",
    ]

    attribution_table = None

    for t in attribution_table_candidates:
        if t in possible_tables:
            attribution_table = t
            break

    if not attribution_table:
        add_result(
            "Attribution table exists",
            "WARNING",
            f"No standard attribution table found. Available tables={possible_tables}",
        )
        con.close()
        return

    required_cols = con.execute(
        f"DESCRIBE {attribution_table}"
    ).fetchdf()["column_name"].tolist()

    needed = {"impression_timestamp", "conversion_timestamp"}

    if not needed.issubset(set(required_cols)):
        add_result(
            "Attribution-window columns",
            "WARNING",
            f"Required timestamp columns not found in {attribution_table}. Columns={required_cols}",
        )
        con.close()
        return

    invalid_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {attribution_table}
        WHERE conversion_timestamp < impression_timestamp
           OR DATE_DIFF('day', impression_timestamp, conversion_timestamp) > 7
        """
    ).fetchone()[0]

    if invalid_count > 0:
        add_result(
            "Attribution-window logic",
            "FAILED",
            f"Invalid attributed rows outside 7-day window={invalid_count}",
        )
    else:
        add_result(
            "Attribution-window logic",
            "PASSED",
            f"All attributed conversions are within valid 7-day window in {attribution_table}",
        )

    con.close()


def run_incremental_lift_qa():
    print("Running incremental lift QA...")

    if not DB_PATH.exists():
        add_result(
            "Incremental lift QA",
            "FAILED",
            "DuckDB database missing",
        )
        return

    con = duckdb.connect(str(DB_PATH))

    possible_tables = con.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchdf()["table_name"].tolist()

    lift_candidates = [
        "marts.mart_campaign_effectiveness",
        "marts.fact_campaign_sessions",
        "intermediate.int_pre_post_spot_sessions",
    ]

    lift_table = None

    for t in lift_candidates:
        if t in possible_tables:
            lift_table = t
            break

    if not lift_table:
        add_result(
            "Incremental lift table exists",
            "WARNING",
            f"No standard incremental lift table found. Available tables={possible_tables}",
        )
        con.close()
        return

    cols = con.execute(f"DESCRIBE {lift_table}").fetchdf()["column_name"].tolist()

    expected_metric_cols = [
        "exposed_conversion_rate",
        "control_conversion_rate",
        "incremental_lift",
    ]

    missing = [c for c in expected_metric_cols if c not in cols]

    if missing:
        add_result(
            "Incremental lift metric columns",
            "WARNING",
            f"Missing expected metric columns in {lift_table}: {missing}",
        )
        con.close()
        return

    invalid_rates = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {lift_table}
        WHERE exposed_conversion_rate < 0
           OR exposed_conversion_rate > 1
           OR control_conversion_rate < 0
           OR control_conversion_rate > 1
        """
    ).fetchone()[0]

    if invalid_rates > 0:
        add_result(
            "Incremental lift rate bounds",
            "FAILED",
            f"Rates outside 0-1 range={invalid_rates}",
        )
    else:
        add_result(
            "Incremental lift rate bounds",
            "PASSED",
            "Conversion rates are within 0-1 range",
        )

    invalid_lift = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {lift_table}
        WHERE incremental_lift IS NULL
        """
    ).fetchone()[0]

    if invalid_lift > 0:
        add_result(
            "Incremental lift null check",
            "FAILED",
            f"Null incremental_lift rows={invalid_lift}",
        )
    else:
        add_result(
            "Incremental lift null check",
            "PASSED",
            "No null incremental lift values",
        )

    con.close()


def run_ml_output_qa():
    print("Running ML output QA...")

    if not DB_PATH.exists():
        add_result(
            "ML output QA",
            "FAILED",
            "DuckDB database missing",
        )
        return

    con = duckdb.connect(str(DB_PATH))

    possible_tables = con.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchdf()["table_name"].tolist()

    ml_candidates = [
        "marts.ml_campaign_response_scores",
        "marts.odec_ready_campaign_dataset",
    ]

    ml_table = None

    for t in ml_candidates:
        if t in possible_tables:
            ml_table = t
            break

    if not ml_table:
        add_result(
            "ML scoring table exists",
            "WARNING",
            f"No standard ML scoring table found. Available tables={possible_tables}",
        )
        con.close()
        return

    cols = con.execute(f"DESCRIBE {ml_table}").fetchdf()["column_name"].tolist()

    probability_cols = [
        c for c in cols if "score" in c.lower() or "prob" in c.lower()
    ]

    if not probability_cols:
        add_result(
            "ML probability column exists",
            "WARNING",
            f"No probability/score column found in {ml_table}. Columns={cols}",
        )
        con.close()
        return

    score_col = probability_cols[0]

    invalid_scores = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {ml_table}
        WHERE {score_col} < 0
           OR {score_col} > 1
           OR {score_col} IS NULL
        """
    ).fetchone()[0]

    if invalid_scores > 0:
        add_result(
            "ML score bounds",
            "FAILED",
            f"Invalid score rows in {ml_table}.{score_col}={invalid_scores}",
        )
    else:
        add_result(
            "ML score bounds",
            "PASSED",
            f"All ML scores in {ml_table}.{score_col} are between 0 and 1",
        )

    row_count = con.execute(f"SELECT COUNT(*) FROM {ml_table}").fetchone()[0]

    if row_count == 0:
        add_result(
            "ML output row count",
            "FAILED",
            f"{ml_table} has 0 rows",
        )
    else:
        add_result(
            "ML output row count",
            "PASSED",
            f"{ml_table} rows={row_count}",
        )

    con.close()


def write_report():
    report = pd.DataFrame(qa_results)
    report_path = Path("qa/reports/qa_report.csv")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(report_path, index=False)

    print("\nQA SUMMARY")
    print(report.to_string(index=False))
    print(f"\nQA report written to: {report_path}")

    failed = report[report["status"] == "FAILED"]

    if len(failed) > 0:
        sys.exit(1)

    print("\nAll blocking QA checks passed.")


def main():
    run_file_level_qa()
    run_schema_qa()
    run_raw_row_count_qa()
    run_duckdb_table_qa()
    run_null_duplicate_qa()
    run_attribution_window_qa()
    run_incremental_lift_qa()
    run_ml_output_qa()
    write_report()


if __name__ == "__main__":
    main()
