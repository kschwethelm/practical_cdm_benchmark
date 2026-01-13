-----------------------------------------
-- Assign hadm_id to radiology reports
-- Run this BEFORE filtering with filter_hadm.sql
-----------------------------------------
--
-- This script assigns hadm_id to radiology reports that are
-- temporally proximal to hospital admissions but don't have hadm_id assigned.
--
-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -f assign_events.sql

SET CLIENT_ENCODING TO 'utf8';

-- Create new table with only assigned radiology reports
-- Using 1 day window before first transfer intime to last transfer intime
-- This matches the original Python implementation
DROP TABLE IF EXISTS mimiciv_note.radiology_assigned;
CREATE TABLE mimiciv_note.radiology_assigned AS
SELECT
    r.note_id,
    r.subject_id,
    subquery.hadm_id,
    r.note_type,
    r.note_seq,
    r.charttime,
    r.storetime,
    r.text
FROM mimiciv_note.radiology r
INNER JOIN (
    SELECT
        a.hadm_id,
        a.subject_id,
        MIN(t.intime) - INTERVAL '1 day' AS start_time,
        MAX(t.intime) AS end_time  -- Last transfer intime, NOT dischtime
    FROM cdm_hosp.admissions a
    JOIN cdm_hosp.transfers t ON a.hadm_id = t.hadm_id
    GROUP BY a.hadm_id, a.subject_id
) subquery ON r.subject_id = subquery.subject_id
    AND r.hadm_id IS NULL
    AND r.charttime >= subquery.start_time
    AND r.charttime <= subquery.end_time;

-- Manual fix for report that was 1 day and 1 hour off
-- From original Python implementation
INSERT INTO mimiciv_note.radiology_assigned
SELECT
    r.note_id,
    r.subject_id,
    21285450 AS hadm_id,
    r.note_type,
    r.note_seq,
    r.charttime,
    r.storetime,
    r.text
FROM mimiciv_note.radiology r
WHERE r.note_id = '13458482-RR-51'
    AND r.hadm_id IS NULL;

SELECT 'Radiology reports newly assigned: ' || COUNT(*) AS status
FROM mimiciv_note.radiology_assigned;

SELECT 'Assignment complete!' AS status;
