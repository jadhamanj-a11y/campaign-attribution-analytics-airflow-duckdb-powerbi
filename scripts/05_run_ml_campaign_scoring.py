from pathlib import Path
import duckdb
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

DB_PATH = "duckdb/campaign_analytics.duckdb"
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("data/output/ml")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def classify_response(row):
    lift = row["incremental_lift_pct"]
    is_abnormal = row["is_abnormal_response"]

    if is_abnormal == 1 and lift is not None and lift > 0:
        return "Abnormal Positive Spike"
    if is_abnormal == 1 and lift is not None and lift < 0:
        return "Abnormal Negative Drop"
    if lift is not None and lift >= 50:
        return "High Positive Lift"
    if lift is not None and lift > 0:
        return "Normal Positive Lift"
    if lift is not None and lift < 0:
        return "Weak Response"
    return "Insufficient Baseline"

def main():
    con = duckdb.connect(DB_PATH)

    df = con.execute("""
        SELECT
            spot_id,
            campaign_id,
            channel_id,
            spot_ts,
            COALESCE(pre_spot_sessions, 0) AS pre_spot_sessions,
            COALESCE(post_spot_sessions, 0) AS post_spot_sessions,
            COALESCE(incremental_lift_pct, 0) AS incremental_lift_pct,
            COALESCE(attributed_sessions, 0) AS attributed_sessions,
            COALESCE(budget, 0) AS budget
        FROM marts.mart_campaign_effectiveness
    """).fetchdf()

    if df.empty:
        raise ValueError("No campaign effectiveness data found for ML scoring.")

    features = [
        "pre_spot_sessions",
        "post_spot_sessions",
        "incremental_lift_pct",
        "attributed_sessions",
        "budget"
    ]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[features])

    model = IsolationForest(
        n_estimators=100,
        contamination=0.25,
        random_state=42
    )

    predictions = model.fit_predict(X_scaled)

    df["anomaly_score"] = model.decision_function(X_scaled)
    df["is_abnormal_response"] = [1 if p == -1 else 0 for p in predictions]
    df["response_segment"] = df.apply(classify_response, axis=1)

    output_file = OUTPUT_DIR / "ml_campaign_response_scores.csv"
    df.to_csv(output_file, index=False)

    joblib.dump(model, MODEL_DIR / "campaign_response_isolation_forest.joblib")
    joblib.dump(scaler, MODEL_DIR / "campaign_response_scaler.joblib")

    con.execute("CREATE SCHEMA IF NOT EXISTS ml")

    con.execute(f"""
        CREATE OR REPLACE TABLE ml.ml_campaign_response_scores AS
        SELECT *
        FROM read_csv_auto('{output_file}')
    """)

    print("\nML Campaign Response Scores:")
    print(df)

    print(f"\nML output written to: {output_file}")
    print("ML scoring table created: ml.ml_campaign_response_scores")

    con.close()

if __name__ == "__main__":
    main()
