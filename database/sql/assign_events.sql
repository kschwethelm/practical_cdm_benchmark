-----------------------------------------
-- Assign hadm_id to lab and microbiology events
-- Run this AFTER loading the filtered data
-----------------------------------------
--
-- This script assigns hadm_id to labevents and microbiologyevents that are
-- temporally proximal to hospital admissions but don't have hadm_id assigned.
--
-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -f assign_events.sql

SET CLIENT_ENCODING TO 'utf8';

-- Count events before assignment
SELECT 'Labevents before assignment: ' || COUNT(*) AS status FROM mimiciv_hosp.labevents;
SELECT 'Labevents with hadm_id: ' || COUNT(*) AS status FROM mimiciv_hosp.labevents WHERE hadm_id IS NOT NULL;

-- Create backup table for labevents
DROP TABLE IF EXISTS mimiciv_hosp.labevents_original;
CREATE TABLE mimiciv_hosp.labevents_original AS SELECT * FROM mimiciv_hosp.labevents;

-- Assign hadm_id to labevents with NULL hadm_id
-- Using 1 day window before admission to discharge
UPDATE mimiciv_hosp.labevents l
SET hadm_id = a.hadm_id
FROM mimiciv_hosp.admissions a
WHERE l.hadm_id IS NULL
    AND l.subject_id = a.subject_id
    AND l.charttime >= a.admittime - INTERVAL '1 day'
    AND l.charttime <= a.dischtime;

-- Count events after assignment
SELECT 'Labevents after assignment: ' || COUNT(*) AS status FROM mimiciv_hosp.labevents;
SELECT 'Labevents with hadm_id: ' || COUNT(*) AS status FROM mimiciv_hosp.labevents WHERE hadm_id IS NOT NULL;
SELECT 'Labevents newly assigned: ' || COUNT(*) AS status FROM mimiciv_hosp.labevents
WHERE hadm_id IS NOT NULL
AND labevent_id IN (SELECT labevent_id FROM mimiciv_hosp.labevents_original WHERE hadm_id IS NULL);

-- Count events before assignment for microbiology
SELECT 'Microbiologyevents before assignment: ' || COUNT(*) AS status FROM mimiciv_hosp.microbiologyevents;
SELECT 'Microbiologyevents with hadm_id: ' || COUNT(*) AS status FROM mimiciv_hosp.microbiologyevents WHERE hadm_id IS NOT NULL;

-- Create backup table for microbiologyevents
DROP TABLE IF EXISTS mimiciv_hosp.microbiologyevents_original;
CREATE TABLE mimiciv_hosp.microbiologyevents_original AS SELECT * FROM mimiciv_hosp.microbiologyevents;

-- Assign hadm_id to microbiologyevents with NULL hadm_id
-- Using 1 day window before admission to discharge
UPDATE mimiciv_hosp.microbiologyevents m
SET hadm_id = a.hadm_id
FROM mimiciv_hosp.admissions a
WHERE m.hadm_id IS NULL
    AND m.subject_id = a.subject_id
    AND m.charttime >= a.admittime - INTERVAL '1 day'
    AND m.charttime <= a.dischtime;

-- Count events after assignment
SELECT 'Microbiologyevents after assignment: ' || COUNT(*) AS status FROM mimiciv_hosp.microbiologyevents;
SELECT 'Microbiologyevents with hadm_id: ' || COUNT(*) AS status FROM mimiciv_hosp.microbiologyevents WHERE hadm_id IS NOT NULL;
SELECT 'Microbiologyevents newly assigned: ' || COUNT(*) AS status FROM mimiciv_hosp.microbiologyevents
WHERE hadm_id IS NOT NULL
AND microevent_id IN (SELECT microevent_id FROM mimiciv_hosp.microbiologyevents_original WHERE hadm_id IS NULL);

-- Optional: Drop backup tables if you're satisfied with the results
-- DROP TABLE IF EXISTS mimiciv_hosp.labevents_original;
-- DROP TABLE IF EXISTS mimiciv_hosp.microbiologyevents_original;

SELECT 'Assignment complete!' AS status;
