-- Distribution of each score within each recruiter decision. Quartiles rather than means
-- alone, because the interesting failures here are shifts in shape, not in centre.
SELECT recruiter_decision,
       count(*)                                                          AS decided,
       avg(rule_score)::float8                                           AS rule_mean,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY rule_score)::float8  AS rule_p25,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY rule_score)::float8  AS rule_median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY rule_score)::float8  AS rule_p75,
       avg(llm_score)::float8                                            AS llm_mean,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY llm_score)::float8   AS llm_p25,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY llm_score)::float8   AS llm_median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY llm_score)::float8   AS llm_p75
FROM scored_applications
WHERE is_decided
  AND (CAST(:exclude_family AS TEXT) IS NULL OR job_family <> CAST(:exclude_family AS TEXT))
GROUP BY recruiter_decision
ORDER BY recruiter_decision;
