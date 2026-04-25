from pathlib import Path
import duckdb

DB_PATH = "duckdb/campaign_analytics.duckdb"
OUTPUT_DIR = Path("data/output")
ODEC_DIR = OUTPUT_DIR / "odec_ready"
PBI_DIR = OUTPUT_DIR / "powerbi"

def main():
    ODEC_DIR.mkdir(parents=True, exist_ok=True)
    PBI_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(DB_PATH)

    exports = {
        "marts.odec_ready_campaign_dataset": ODEC_DIR / "odec_ready_campaign_dataset.csv",
        "marts.mart_campaign_effectiveness": PBI_DIR / "mart_campaign_effectiveness.csv",
        "marts.fact_campaign_sessions": PBI_DIR / "fact_campaign_sessions.csv",
    }

    for table, path in exports.items():
        con.execute(f"""
            COPY {table}
            TO '{path}'
            WITH (HEADER, DELIMITER ',')
        """)
        print(f"Exported {table} → {path}")

    con.close()
    print("Output export completed successfully.")

if __name__ == "__main__":
    main()
