from pathlib import Path
import duckdb

DB_PATH = "duckdb/campaign_analytics.duckdb"
PBI_DIR = Path("data/output/powerbi")

def main():
    PBI_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(DB_PATH)

    con.execute(f"""
        COPY ml.ml_campaign_response_scores
        TO '{PBI_DIR / "ml_campaign_response_scores.csv"}'
        WITH (HEADER, DELIMITER ',')
    """)

    con.close()

    print("Exported ML campaign response scores to Power BI output folder.")

if __name__ == "__main__":
    main()
