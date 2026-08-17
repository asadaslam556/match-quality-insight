-- Interaction funnel, plus the check that shortlisting is not usable as an input signal:
-- positive_rate_when_shortlisted comes out at exactly 1.0, which means the event records
-- the decision rather than predicting it.
WITH per_application AS (
    SELECT s.application_id,
           s.is_decided,
           s.is_positive,
           (count(e.event_id) FILTER (WHERE e.event_type = 'profile_opened'))  > 0 AS opened,
           (count(e.event_id) FILTER (WHERE e.event_type = 'ai_score_viewed')) > 0 AS ai_viewed,
           (count(e.event_id) FILTER (WHERE e.event_type = 'shortlisted'))     > 0 AS shortlisted
    FROM scored_applications s
             LEFT JOIN recruiter_events e ON e.application_id = s.application_id
    GROUP BY 1, 2, 3
)
SELECT count(*)                                                   AS applications,
       count(*) FILTER (WHERE opened)                             AS profile_opened,
       count(*) FILTER (WHERE ai_viewed)                          AS ai_score_viewed,
       count(*) FILTER (WHERE shortlisted)                        AS shortlisted,
       count(*) FILTER (WHERE NOT opened AND NOT ai_viewed
                              AND NOT shortlisted)                AS no_events,
       (avg(is_positive::int)
            FILTER (WHERE is_decided AND shortlisted))::float8    AS positive_rate_when_shortlisted,
       (avg(is_positive::int)
            FILTER (WHERE is_decided AND NOT shortlisted))::float8 AS positive_rate_when_not_shortlisted,
       (avg(is_positive::int)
            FILTER (WHERE is_decided AND ai_viewed))::float8      AS positive_rate_when_ai_viewed,
       (avg(is_positive::int)
            FILTER (WHERE is_decided AND NOT ai_viewed))::float8  AS positive_rate_when_ai_not_viewed
FROM per_application;
