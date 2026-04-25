from pathlib import Path
import duckdb

DB_PATH = "duckdb/campaign_analytics.duckdb"

RAW_FILES = {
    "raw.grp_spots": "data/raw/grp_spots/grp_spots.csv",
    "raw.sessions": "data/raw/sessions/sessions.csv",
    "raw.campaign_master": "data/raw/campaign_master/campaign_master.csv",
    "raw.odec_mapping": "data/raw/odec/odec_mapping.csv",
}

def main():
    Path("duckdb").mkdir(exist_ok=True)
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")

    for table_name, file_path in RAW_FILES.items():
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Missing required file: {file_path}")

        con.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT
                *,
                current_timestamp AS ingestion_ts
            FROM read_csv_auto('{file_path}', header=true)
        """)

        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        con.execute("""
            CREATE TABLE IF NOT EXISTS audit.ingestion_log (
                table_name VARCHAR,
                file_path VARCHAR,
                row_count INTEGER,
                status VARCHAR,
                ingestion_ts TIMESTAMP
            )
        """)

        con.execute(
            """
            INSERT INTO audit.ingestion_log
            VALUES (?, ?, ?, ?, current_timestamp)
            """,
            [table_name, file_path, count, "SUCCESS"],
        )

        print(f"Loaded {table_name}: {count} rows")

    con.close()
    print("Raw ingestion completed successfully.")

if __name__ == "__main__":
    main()
