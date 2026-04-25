from pathlib import Path
import duckdb
import matplotlib.pyplot as plt

DB_PATH = "duckdb/campaign_analytics.duckdb"
VISUAL_DIR = Path("visuals")
VISUAL_DIR.mkdir(exist_ok=True)

con = duckdb.connect(DB_PATH)

campaign_df = con.execute("""
    SELECT
        campaign_id,
        channel_id,
        spot_id,
        pre_spot_sessions,
        post_spot_sessions,
        incremental_lift_pct,
        attributed_sessions
    FROM marts.mart_campaign_effectiveness
    ORDER BY spot_id
""").fetchdf()

ml_df = con.execute("""
    SELECT
        spot_id,
        campaign_id,
        incremental_lift_pct,
        anomaly_score,
        is_abnormal_response,
        response_segment
    FROM ml.ml_campaign_response_scores
    ORDER BY spot_id
""").fetchdf()

con.close()

# Chart 1: Pre vs Post Sessions
plt.figure(figsize=(10, 6))
x = range(len(campaign_df))
plt.bar([i - 0.2 for i in x], campaign_df["pre_spot_sessions"], width=0.4, label="Pre Spot Sessions")
plt.bar([i + 0.2 for i in x], campaign_df["post_spot_sessions"], width=0.4, label="Post Spot Sessions")
plt.xticks(x, campaign_df["spot_id"])
plt.xlabel("Spot ID")
plt.ylabel("Session Count")
plt.title("Pre vs Post Spot Sessions")
plt.legend()
plt.tight_layout()
plt.savefig(VISUAL_DIR / "pre_vs_post_sessions.png")
plt.close()

# Chart 2: Incremental Lift by Spot
plt.figure(figsize=(10, 6))
plt.bar(campaign_df["spot_id"], campaign_df["incremental_lift_pct"].fillna(0))
plt.xlabel("Spot ID")
plt.ylabel("Incremental Lift %")
plt.title("Incremental Lift % by Campaign Spot")
plt.tight_layout()
plt.savefig(VISUAL_DIR / "incremental_lift_by_spot.png")
plt.close()

# Chart 3: Attributed Sessions by Spot
plt.figure(figsize=(10, 6))
plt.bar(campaign_df["spot_id"], campaign_df["attributed_sessions"])
plt.xlabel("Spot ID")
plt.ylabel("Attributed Sessions")
plt.title("Attributed Sessions by Campaign Spot")
plt.tight_layout()
plt.savefig(VISUAL_DIR / "attributed_sessions_by_spot.png")
plt.close()

# Chart 4: ML Anomaly Score
plt.figure(figsize=(10, 6))
plt.bar(ml_df["spot_id"], ml_df["anomaly_score"])
plt.xlabel("Spot ID")
plt.ylabel("Anomaly Score")
plt.title("ML Campaign Response Anomaly Score")
plt.tight_layout()
plt.savefig(VISUAL_DIR / "ml_anomaly_score_by_spot.png")
plt.close()

print("Visuals generated successfully:")
for file in VISUAL_DIR.glob("*.png"):
    print(file)
