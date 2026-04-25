import duckdb
import sys

DB_PATH = "duckdb/campaign_analytics.duckdb"
DQ_SQL_FILE = "sql/02_data_quality_checks.sql"

def main():
    con = duckdb.connect(DB_PATH)

    with open(DQ_SQL_FILE, "r", encoding="utf-8") as f:
        dq_sql = f.read()

    con.execute(dq_sql)

    results = con.execute("""
        SELECT *
        FROM dq.dq_results
        ORDER BY failed_rows DESC
    """).fetchdf()

    print("\nData Quality Results:")
    print(results)

    total_failures = con.execute("""
        SELECT SUM(failed_rows)
        FROM dq.dq_results
    """).fetchone()[0]

    con.close()

    if total_failures and total_failures > 0:
        raise Exception(f"Data quality checks failed. Total failed rows: {total_failures}")

    print("All data quality checks passed successfully.")

if __name__ == "__main__":
    main()
