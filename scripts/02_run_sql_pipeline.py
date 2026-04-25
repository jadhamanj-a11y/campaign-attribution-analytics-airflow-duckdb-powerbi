import duckdb

DB_PATH = "duckdb/campaign_analytics.duckdb"
SQL_FILE = "sql/01_campaign_transformations.sql"

def main():
    con = duckdb.connect(DB_PATH)

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    con.execute(sql)

    checks = [
        "intermediate.int_session_campaign_candidates",
        "intermediate.int_attributed_sessions",
        "marts.fact_campaign_sessions",
        "marts.mart_campaign_effectiveness",
        "marts.odec_ready_campaign_dataset",
    ]

    for table in checks:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")

    con.close()
    print("SQL transformation pipeline completed successfully.")

if __name__ == "__main__":
    main()
