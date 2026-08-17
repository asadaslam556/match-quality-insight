-- Raw scores per model version, feeding the drift comparison in the quality gate.
-- Pending applications are kept here on purpose: score drift is a property of the scorer,
-- not of the recruiter decisions, so it should be measured on everything that was scored.
SELECT llm_model_version,
       llm_score::float8  AS llm_score,
       rule_score::float8 AS rule_score
FROM scored_applications;
