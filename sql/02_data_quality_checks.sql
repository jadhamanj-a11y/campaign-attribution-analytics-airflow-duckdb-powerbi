CREATE SCHEMA IF NOT EXISTS dq;

CREATE OR REPLACE TABLE dq.dq_results AS

SELECT
    'raw.grp_spots' AS table_name,
    'spot_id_not_null' AS check_name,
    COUNT(*) AS failed_rows
FROM raw.grp_spots
WHERE spot_id IS NULL

UNION ALL

SELECT
    'raw.grp_spots',
    'campaign_id_not_null',
    COUNT(*)
FROM raw.grp_spots
WHERE campaign_id IS NULL

UNION ALL

SELECT
    'raw.sessions',
    'session_id_not_null',
    COUNT(*)
FROM raw.sessions
WHERE session_id IS NULL

UNION ALL

SELECT
    'raw.sessions',
    'session_timestamp_not_null',
    COUNT(*)
FROM raw.sessions
WHERE session_timestamp IS NULL

UNION ALL

SELECT
    'marts.fact_campaign_sessions',
    'no_duplicate_attributed_sessions',
    COUNT(*)
FROM (
    SELECT session_id
    FROM marts.fact_campaign_sessions
    GROUP BY session_id
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT
    'marts.fact_campaign_sessions',
    'valid_attribution_window',
    COUNT(*)
FROM marts.fact_campaign_sessions
WHERE minutes_after_spot < 0
   OR minutes_after_spot > 15

UNION ALL

SELECT
    'marts.mart_campaign_effectiveness',
    'non_negative_session_counts',
    COUNT(*)
FROM marts.mart_campaign_effectiveness
WHERE pre_spot_sessions < 0
   OR post_spot_sessions < 0;
