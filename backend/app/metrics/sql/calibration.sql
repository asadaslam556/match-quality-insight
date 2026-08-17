-- Does a given score band convert at the rate the score implies? Split by model version so
-- a recalibration between versions shows up as two separated curves.
-- rule_score is put on the same 0-100 axis so one query serves both scorers.
WITH normalised AS (
    SELECT llm_model_version,
           is_positive,
           CASE WHEN CAST(:scorer AS TEXT) = 'rule'
                    THEN rule_score::float8 * 100
                    ELSE llm_score::float8
           END AS score
    FROM scored_applications
    WHERE is_decided
      AND (CAST(:exclude_family AS TEXT) IS NULL OR job_family <> CAST(:exclude_family AS TEXT))
)
SELECT llm_model_version,
       -- width_bucket returns 11 for a score of exactly 100, so it is folded into the top band
       least(width_bucket(score, 0, 100, 10), 10)      AS band,
       count(*)                                        AS decided,
       count(*) FILTER (WHERE is_positive)             AS positives,
       avg(is_positive::int)::float8                   AS positive_rate,
       avg(score)::float8                              AS mean_score
FROM normalised
GROUP BY 1, 2
ORDER BY 1, 2;
