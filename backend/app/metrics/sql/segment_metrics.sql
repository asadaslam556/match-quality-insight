-- Per-segment counts and mean scores. Positive rate and its confidence interval are
-- derived in Python from positives/decided so the interval logic lives in one place.
SELECT {dimension}                                            AS segment,
       count(*)                                               AS applications,
       count(*) FILTER (WHERE is_decided)                     AS decided,
       count(*) FILTER (WHERE is_decided AND is_positive)     AS positives,
       avg(rule_score)::float8                                AS mean_rule_score,
       avg(llm_score)::float8                                 AS mean_llm_score,
       avg((rule_fit = 'good')::int)::float8                  AS good_fit_rate,
       avg((rule_fit = 'low')::int)::float8                   AS low_fit_rate
FROM scored_applications
GROUP BY 1
ORDER BY 1;
