-- Where the two scorers land applications relative to each other, and how each cell
-- actually converted. The rule_fit bucket is the product's own label, so the matrix is
-- read the same way a recruiter would see it in the UI.
SELECT rule_fit,
       CASE
           WHEN llm_score < 50 THEN '0-49'
           WHEN llm_score < 65 THEN '50-64'
           WHEN llm_score < 80 THEN '65-79'
           ELSE '80-100'
       END                                                AS llm_band,
       count(*)                                           AS decided,
       count(*) FILTER (WHERE is_positive)                AS positives,
       avg(is_positive::int)::float8                      AS positive_rate
FROM scored_applications
WHERE is_decided
GROUP BY 1, 2
ORDER BY 1, 2;
