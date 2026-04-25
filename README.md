## Power BI Dashboard Layer

The project exports curated DuckDB marts into CSV files under `data/powerbi/` for dashboard creation in Power BI Desktop.

### Power BI Datasets

| File | Purpose |
|---|---|
| `campaign_effectiveness.csv` | Campaign-level effectiveness, attributed sessions, lift, and budget |
| `fact_campaign_sessions.csv` | Session-level campaign attribution fact table |
| `ml_campaign_response_scores.csv` | ML-generated campaign response scoring output |
| `odec_ready_campaign_dataset.csv` | ODEC/channel-ready analytical dataset |

### Recommended Dashboard Pages

1. **Executive Campaign Performance**
   - Total campaigns
   - Total attributed sessions
   - Average incremental lift %
   - Budget by campaign
   - Campaign effectiveness ranking

2. **Channel and GRP Analysis**
   - GRP by channel
   - Sessions after ad spots
   - Attributed sessions by channel
   - Campaign performance by channel type

3. **ML Response Scoring**
   - Response score distribution
   - High-propensity user/session segments
   - Campaign response ranking
   - Device and source-level response patterns

### Power BI Import Steps

1. Open Power BI Desktop.
2. Select **Get Data → Text/CSV**.
3. Import files from `data/powerbi/`.
4. Build relationships using available keys such as `campaign_id`, `channel_id`, and `session_id`.
5. Create measures for total sessions, attributed sessions, incremental lift, average response score, and campaign ranking.
