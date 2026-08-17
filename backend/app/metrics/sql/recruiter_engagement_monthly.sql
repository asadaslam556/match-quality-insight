-- Monthly share of applications that reached each interaction stage.
-- LEFT JOIN, not INNER: 109 applications have no recruiter events at all and dropping them
-- would quietly inflate every rate below.
WITH per_application AS (
    SELECT s.application_id,
           s.created_month,
           (count(e.event_id) FILTER (WHERE e.event_type = 'profile_opened'))  > 0 AS opened,
           (count(e.event_id) FILTER (WHERE e.event_type = 'ai_score_viewed')) > 0 AS ai_viewed,
           (count(e.event_id) FILTER (WHERE e.event_type = 'shortlisted'))     > 0 AS shortlisted
    FROM scored_applications s
             LEFT JOIN recruiter_events e ON e.application_id = s.application_id
    GROUP BY 1, 2
)
SELECT created_month                       AS month,
       count(*)                            AS applications,
       avg(opened::int)::float8            AS profile_opened_rate,
       avg(ai_viewed::int)::float8         AS ai_score_viewed_rate,
       avg(shortlisted::int)::float8       AS shortlisted_rate
FROM per_application
GROUP BY 1
ORDER BY 1;
