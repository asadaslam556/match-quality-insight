-- Headline counts for the dashboard landing page.
-- FILTER is used instead of CASE so pending rows are excluded from rate denominators
-- rather than silently counted as negatives.
SELECT count(*)                                                          AS total_applications,
       count(*) FILTER (WHERE is_decided)                                AS decided,
       count(*) FILTER (WHERE NOT is_decided)                            AS pending,
       avg((NOT is_decided)::int)::float8                                AS pending_rate,
       (avg(is_positive::int) FILTER (WHERE is_decided))::float8         AS positive_rate,
       (avg((recruiter_decision = 'hired')::int)
            FILTER (WHERE is_decided))::float8                           AS hire_rate,
       count(DISTINCT job_id)                                            AS jobs,
       count(DISTINCT candidate_id)                                      AS candidates,
       min(created_at)                                                   AS first_application,
       max(created_at)                                                   AS last_application
FROM scored_applications;
