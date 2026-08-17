-- Split each scorer at its own median, then compare outcomes across the four quadrants.
-- Each scorer is cut on its own scale because the two are not comparable in raw units,
-- and because the rule scorer's scale is broken for one job family.
WITH cuts AS (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY rule_score) AS rule_median,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY llm_score)  AS llm_median
    FROM scored_applications
    WHERE is_decided
      AND (CAST(:exclude_family AS TEXT) IS NULL OR job_family <> CAST(:exclude_family AS TEXT))
)
SELECT CASE
           WHEN s.rule_score >= c.rule_median AND s.llm_score >= c.llm_median THEN 'both_high'
           WHEN s.rule_score <  c.rule_median AND s.llm_score <  c.llm_median THEN 'both_low'
           WHEN s.rule_score >= c.rule_median                                 THEN 'rule_high_llm_low'
           ELSE 'llm_high_rule_low'
       END                                       AS quadrant,
       count(*)                                  AS decided,
       count(*) FILTER (WHERE s.is_positive)     AS positives,
       avg(s.is_positive::int)::float8           AS positive_rate
FROM scored_applications s
         CROSS JOIN cuts c
WHERE s.is_decided
  AND (CAST(:exclude_family AS TEXT) IS NULL OR s.job_family <> CAST(:exclude_family AS TEXT))
GROUP BY 1
ORDER BY 1;
