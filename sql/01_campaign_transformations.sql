CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW staging.stg_grp_spots AS
SELECT
    spot_id,
    campaign_id,
    channel_id,
    CAST(spot_date || ' ' || spot_time AS TIMESTAMP) AS spot_ts,
    CAST(spot_date AS DATE) AS spot_date,
    CAST(grp_value AS DOUBLE) AS grp_value,
    CAST(spot_duration_sec AS INTEGER) AS spot_duration_sec
FROM raw.grp_spots;

CREATE OR REPLACE VIEW staging.stg_sessions AS
SELECT
    session_id,
    user_id,
    CAST(session_timestamp AS TIMESTAMP) AS session_ts,
    LOWER(TRIM(device_type)) AS device_type,
    LOWER(TRIM(session_source)) AS session_source
FROM raw.sessions;

CREATE OR REPLACE VIEW staging.stg_campaign_master AS
SELECT
    campaign_id,
    campaign_name,
    brand,
    CAST(start_date AS DATE) AS start_date,
    CAST(end_date AS DATE) AS end_date,
    CAST(budget AS DOUBLE) AS budget
FROM raw.campaign_master;

CREATE OR REPLACE VIEW staging.stg_odec_mapping AS
SELECT
    channel_id,
    odec_channel_code,
    channel_name,
    channel_type
FROM raw.odec_mapping;

CREATE OR REPLACE TABLE intermediate.int_session_campaign_candidates AS
SELECT
    s.session_id,
    s.user_id,
    s.session_ts,
    s.device_type,
    s.session_source,
    g.spot_id,
    g.campaign_id,
    g.channel_id,
    g.spot_ts,
    g.spot_date,
    g.grp_value,
    date_diff('minute', g.spot_ts, s.session_ts) AS minutes_after_spot
FROM staging.stg_sessions s
JOIN staging.stg_grp_spots g
    ON s.session_ts BETWEEN g.spot_ts AND g.spot_ts + INTERVAL '15 minutes';

CREATE OR REPLACE TABLE intermediate.int_attributed_sessions AS
SELECT *
FROM (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY session_id
            ORDER BY minutes_after_spot ASC
        ) AS attribution_rank
    FROM intermediate.int_session_campaign_candidates
)
WHERE attribution_rank = 1;

CREATE OR REPLACE TABLE intermediate.int_pre_post_spot_sessions AS
SELECT
    g.spot_id,
    g.campaign_id,
    g.channel_id,
    g.spot_ts,
    SUM(
        CASE
            WHEN s.session_ts BETWEEN g.spot_ts - INTERVAL '15 minutes'
                                  AND g.spot_ts
            THEN 1 ELSE 0
        END
    ) AS pre_spot_sessions,
    SUM(
        CASE
            WHEN s.session_ts BETWEEN g.spot_ts
                                  AND g.spot_ts + INTERVAL '15 minutes'
            THEN 1 ELSE 0
        END
    ) AS post_spot_sessions
FROM staging.stg_grp_spots g
LEFT JOIN staging.stg_sessions s
    ON s.session_ts BETWEEN g.spot_ts - INTERVAL '15 minutes'
                        AND g.spot_ts + INTERVAL '15 minutes'
GROUP BY
    g.spot_id,
    g.campaign_id,
    g.channel_id,
    g.spot_ts;

CREATE OR REPLACE TABLE marts.fact_campaign_sessions AS
SELECT
    a.session_id,
    a.user_id,
    a.session_ts,
    a.spot_id,
    a.campaign_id,
    cm.campaign_name,
    cm.brand,
    a.channel_id,
    om.odec_channel_code,
    om.channel_name,
    om.channel_type,
    a.spot_ts,
    a.minutes_after_spot,
    a.grp_value,
    1 AS attribution_flag
FROM intermediate.int_attributed_sessions a
LEFT JOIN staging.stg_campaign_master cm
    ON a.campaign_id = cm.campaign_id
LEFT JOIN staging.stg_odec_mapping om
    ON a.channel_id = om.channel_id;

CREATE OR REPLACE TABLE marts.mart_campaign_effectiveness AS
SELECT
    p.spot_id,
    p.campaign_id,
    cm.campaign_name,
    cm.brand,
    p.channel_id,
    om.channel_name,
    om.channel_type,
    p.spot_ts,
    p.pre_spot_sessions,
    p.post_spot_sessions,
    CASE
        WHEN p.pre_spot_sessions = 0 THEN NULL
        ELSE ROUND(
            ((p.post_spot_sessions - p.pre_spot_sessions) * 100.0)
            / p.pre_spot_sessions,
            2
        )
    END AS incremental_lift_pct,
    COALESCE(attr.attributed_sessions, 0) AS attributed_sessions,
    cm.budget
FROM intermediate.int_pre_post_spot_sessions p
LEFT JOIN (
    SELECT
        spot_id,
        COUNT(DISTINCT session_id) AS attributed_sessions
    FROM marts.fact_campaign_sessions
    GROUP BY spot_id
) attr
    ON p.spot_id = attr.spot_id
LEFT JOIN staging.stg_campaign_master cm
    ON p.campaign_id = cm.campaign_id
LEFT JOIN staging.stg_odec_mapping om
    ON p.channel_id = om.channel_id;

CREATE OR REPLACE TABLE marts.odec_ready_campaign_dataset AS
SELECT
    campaign_id,
    campaign_name,
    brand,
    channel_id,
    odec_channel_code,
    channel_name,
    channel_type,
    spot_id,
    spot_ts,
    session_id,
    session_ts,
    minutes_after_spot,
    grp_value,
    attribution_flag
FROM marts.fact_campaign_sessions;
