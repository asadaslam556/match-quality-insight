-- One row per decided application, for the metrics that need the full ranked array
-- (AUC, precision@k, threshold sweeps). {dimension} is substituted from a whitelist
-- in queries.py, never from raw request input.
SELECT {dimension}      AS segment,
       is_positive::int AS label,
       rule_score::float8 AS rule_score,
       llm_score::float8  AS llm_score
FROM scored_applications
WHERE is_decided
  AND (CAST(:exclude_family AS TEXT) IS NULL OR job_family <> CAST(:exclude_family AS TEXT));
