-----------------------------------------
-- Assign hadm_id to lab and microbiology events
-- Run this BEFORE filtering with filter_hadm.sql
-----------------------------------------
--
-- This script assigns hadm_id to labevents and microbiologyevents that are
-- temporally proximal to hospital admissions but don't have hadm_id assigned.
--
-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -f assign_events.sql

SET CLIENT_ENCODING TO 'utf8';

-- Create new table with only assigned lab events
-- Using 1 day window before first transfer intime to last transfer intime
-- This matches the original Python implementation
DROP TABLE IF EXISTS mimiciv_hosp.labevents_assigned;
CREATE TABLE mimiciv_hosp.labevents_assigned AS
SELECT
    l.labevent_id,
    l.subject_id,
    subquery.hadm_id,
    l.specimen_id,
    l.itemid,
    l.charttime,
    l.storetime,
    l.value,
    l.valuenum,
    l.valueuom,
    l.ref_range_lower,
    l.ref_range_upper,
    l.flag,
    l.priority,
    l.comments
FROM mimiciv_hosp.labevents l
INNER JOIN (
    SELECT
        a.hadm_id,
        a.subject_id,
        MIN(t.intime) - INTERVAL '1 day' AS start_time,
        MAX(t.intime) AS end_time  -- Last transfer intime, NOT dischtime
    FROM mimiciv_hosp.admissions a
    JOIN mimiciv_hosp.transfers t ON a.hadm_id = t.hadm_id
    GROUP BY a.hadm_id, a.subject_id
) subquery ON l.subject_id = subquery.subject_id
    AND l.hadm_id IS NULL
    AND l.charttime >= subquery.start_time
    AND l.charttime <= subquery.end_time;

SELECT 'Labevents newly assigned: ' || COUNT(*) AS status
FROM mimiciv_hosp.labevents_assigned;

-- Create new table with only assigned microbiology events
-- Using 1 day window before first transfer intime to last transfer intime
-- This matches the original Python implementation
DROP TABLE IF EXISTS mimiciv_hosp.microbiologyevents_assigned;
CREATE TABLE mimiciv_hosp.microbiologyevents_assigned AS
SELECT
    m.microevent_id,
    m.subject_id,
    subquery.hadm_id,
    m.micro_specimen_id,
    m.chartdate,
    m.charttime,
    m.spec_itemid,
    m.spec_type_desc,
    m.test_seq,
    m.storedate,
    m.storetime,
    m.test_itemid,
    m.test_name,
    m.org_itemid,
    m.org_name,
    m.isolate_num,
    m.quantity,
    m.ab_itemid,
    m.ab_name,
    m.dilution_text,
    m.dilution_comparison,
    m.dilution_value,
    m.interpretation,
    m.comments
FROM mimiciv_hosp.microbiologyevents m
INNER JOIN (
    SELECT
        a.hadm_id,
        a.subject_id,
        MIN(t.intime) - INTERVAL '1 day' AS start_time,
        MAX(t.intime) AS end_time  -- Last transfer intime, NOT dischtime
    FROM mimiciv_hosp.admissions a
    JOIN mimiciv_hosp.transfers t ON a.hadm_id = t.hadm_id
    GROUP BY a.hadm_id, a.subject_id
) subquery ON m.subject_id = subquery.subject_id
    AND m.hadm_id IS NULL
    AND m.charttime >= subquery.start_time
    AND m.charttime <= subquery.end_time;

SELECT 'Microbiologyevents newly assigned: ' || COUNT(*) AS status
FROM mimiciv_hosp.microbiologyevents_assigned;

SELECT 'Assignment complete!' AS status;
