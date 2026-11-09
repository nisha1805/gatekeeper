-- Append-only audit log for the compliance service.
-- The application role can read and add rows. It cannot change or delete them.
-- Triggers also block changes for every other role. A database administrator can
-- still disable triggers, so this protects against the app and against accidents,
-- not against a hostile administrator.

CREATE TABLE IF NOT EXISTS assessments (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    system_name   text NOT NULL,
    request       jsonb NOT NULL,
    assessment    jsonb NOT NULL,
    rules_version text NOT NULL
);

CREATE TABLE IF NOT EXISTS review_events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL REFERENCES assessments (id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    decision      text NOT NULL CHECK (decision IN ('approved', 'rejected')),
    reviewer      text NOT NULL,
    comment       text
);

CREATE INDEX IF NOT EXISTS review_events_by_assessment
    ON review_events (assessment_id, created_at);

CREATE OR REPLACE FUNCTION forbid_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit tables are append-only: % is not allowed on %', TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS assessments_rows_append_only ON assessments;
CREATE TRIGGER assessments_rows_append_only
    BEFORE UPDATE OR DELETE ON assessments
    FOR EACH ROW EXECUTE FUNCTION forbid_change();

DROP TRIGGER IF EXISTS assessments_truncate_blocked ON assessments;
CREATE TRIGGER assessments_truncate_blocked
    BEFORE TRUNCATE ON assessments
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();

DROP TRIGGER IF EXISTS review_events_rows_append_only ON review_events;
CREATE TRIGGER review_events_rows_append_only
    BEFORE UPDATE OR DELETE ON review_events
    FOR EACH ROW EXECUTE FUNCTION forbid_change();

DROP TRIGGER IF EXISTS review_events_truncate_blocked ON review_events;
CREATE TRIGGER review_events_truncate_blocked
    BEFORE TRUNCATE ON review_events
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();

-- Each assessment with its latest review decision, if any.
CREATE OR REPLACE VIEW assessments_with_review AS
SELECT a.id, a.created_at, a.system_name, a.request, a.assessment, a.rules_version,
       r.decision AS review_decision, r.reviewer, r.created_at AS reviewed_at
FROM assessments a
LEFT JOIN LATERAL (
    SELECT decision, reviewer, created_at
    FROM review_events
    WHERE assessment_id = a.id
    ORDER BY created_at DESC, id DESC
    LIMIT 1
) r ON true;

GRANT USAGE ON SCHEMA public TO compliance_app;
GRANT SELECT, INSERT ON assessments, review_events TO compliance_app;
GRANT SELECT ON assessments_with_review TO compliance_app;