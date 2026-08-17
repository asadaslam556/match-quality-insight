-- Schema for the match quality dataset. Safe to re-run: everything is dropped first.

DROP VIEW IF EXISTS scored_applications;
DROP TABLE IF EXISTS recruiter_events;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS candidates;

CREATE TABLE candidates (
    candidate_id         TEXT PRIMARY KEY,
    country              TEXT         NOT NULL,
    years_experience     INTEGER      NOT NULL CHECK (years_experience >= 0),
    preferred_job_family TEXT         NOT NULL,
    profile_completeness NUMERIC(4,3) NOT NULL CHECK (profile_completeness BETWEEN 0 AND 1)
);

CREATE TABLE jobs (
    job_id     TEXT PRIMARY KEY,
    country    TEXT NOT NULL,
    job_family TEXT NOT NULL,
    seniority  TEXT NOT NULL CHECK (seniority IN ('junior', 'mid', 'senior')),
    created_at DATE NOT NULL
);

-- No unique constraint on (job_id, candidate_id): the source data contains 243 repeat
-- applications from the same candidate to the same job. See README, "Assumptions".
CREATE TABLE applications (
    application_id     TEXT PRIMARY KEY,
    job_id             TEXT         NOT NULL REFERENCES jobs (job_id),
    candidate_id       TEXT         NOT NULL REFERENCES candidates (candidate_id),
    created_at         TIMESTAMP    NOT NULL,
    rule_score         NUMERIC(4,3) NOT NULL CHECK (rule_score BETWEEN 0 AND 1),
    rule_fit           TEXT         NOT NULL CHECK (rule_fit IN ('low', 'medium', 'good')),
    llm_score          INTEGER      NOT NULL CHECK (llm_score BETWEEN 0 AND 100),
    llm_model_version  TEXT         NOT NULL,
    recruiter_decision TEXT         CHECK (recruiter_decision IN ('rejected', 'interviewed', 'hired')),
    decision_at        TIMESTAMP,
    -- A decision needs a timestamp and vice versa; pending rows have neither.
    CHECK ((recruiter_decision IS NULL) = (decision_at IS NULL)),
    CHECK (decision_at IS NULL OR decision_at >= created_at)
);

CREATE TABLE recruiter_events (
    event_id       TEXT      PRIMARY KEY,
    application_id TEXT      NOT NULL REFERENCES applications (application_id),
    recruiter_id   TEXT      NOT NULL,
    event_type     TEXT      NOT NULL CHECK (event_type IN ('profile_opened', 'ai_score_viewed', 'shortlisted')),
    created_at     TIMESTAMP NOT NULL
);

CREATE INDEX idx_applications_job ON applications (job_id);
CREATE INDEX idx_applications_candidate ON applications (candidate_id);
CREATE INDEX idx_applications_version ON applications (llm_model_version);
CREATE INDEX idx_applications_created ON applications (created_at);
CREATE INDEX idx_events_application ON recruiter_events (application_id);
CREATE INDEX idx_events_type ON recruiter_events (event_type);

-- Every metric query reads from this view rather than re-joining the base tables.
-- It is the single place where two decisions live:
--   1. what counts as a positive outcome
--   2. how profile_completeness is banded
-- The 0.4 band edge is not arbitrary: mean llm_score jumps from 74.0 to 61.7 across it.
CREATE VIEW scored_applications AS
SELECT a.application_id,
       a.job_id,
       a.candidate_id,
       a.created_at,
       a.rule_score,
       a.rule_fit,
       a.llm_score,
       a.llm_model_version,
       a.recruiter_decision,
       a.decision_at,
       j.job_family,
       j.seniority,
       j.country                                            AS job_country,
       c.country                                            AS candidate_country,
       c.years_experience,
       c.profile_completeness,
       c.preferred_job_family,
       a.recruiter_decision IS NOT NULL                     AS is_decided,
       a.recruiter_decision IN ('interviewed', 'hired')      AS is_positive,
       date_trunc('month', a.created_at)::date              AS created_month,
       CASE
           WHEN c.profile_completeness < 0.4 THEN 'thin (<0.4)'
           WHEN c.profile_completeness < 0.7 THEN 'partial (0.4-0.7)'
           ELSE 'complete (>=0.7)'
       END                                                  AS profile_band
FROM applications a
         JOIN jobs j ON j.job_id = a.job_id
         JOIN candidates c ON c.candidate_id = a.candidate_id;
