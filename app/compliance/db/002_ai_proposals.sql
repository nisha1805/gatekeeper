-- What the AI proposed, stored next to what the person finally answered.
-- Same rules as 001: the app role can read and add rows, nobody can change or
-- delete them through the app. The description itself is NOT stored, only a hash,
-- so no free text from the user sits in the audit log. The proposals keep the short
-- quotes the AI copied from the description.
--
-- Safe to run again.

CREATE TABLE IF NOT EXISTS extraction_events (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    model              text NOT NULL,
    description_sha256 text NOT NULL,
    result             jsonb NOT NULL
);

DROP TRIGGER IF EXISTS extraction_events_rows_append_only ON extraction_events;
CREATE TRIGGER extraction_events_rows_append_only
    BEFORE UPDATE OR DELETE ON extraction_events
    FOR EACH ROW EXECUTE FUNCTION forbid_change();

DROP TRIGGER IF EXISTS extraction_events_truncate_blocked ON extraction_events;
CREATE TRIGGER extraction_events_truncate_blocked
    BEFORE TRUNCATE ON extraction_events
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_change();

-- Which AI proposals (if any) an assessment started from.
ALTER TABLE assessments
    ADD COLUMN IF NOT EXISTS extraction_id uuid REFERENCES extraction_events (id);

-- 001's view stays as it is, so 001 can be applied again. This view adds the link.
CREATE OR REPLACE VIEW assessment_records AS
SELECT w.*, a.extraction_id
FROM assessments_with_review w
JOIN assessments a ON a.id = w.id;

GRANT SELECT, INSERT ON extraction_events TO compliance_app;
GRANT SELECT ON assessment_records TO compliance_app;
