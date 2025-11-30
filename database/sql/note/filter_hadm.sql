-----------------------------------------
-- Filter MIMIC-IV-Note data by hadm_id list
-- Run this AFTER loading note data
-----------------------------------------
--
-- This script filters all MIMIC-IV note tables to only include data
-- related to the hospital admissions in the provided hadm_id list.
-- Creates a new schema 'cdm_note' with filtered data, then drops 'mimiciv_note'.
--
-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -f filter_hadm.sql

SET CLIENT_ENCODING TO 'utf8';

-- Create temporary table for hadm_id filtering
DROP TABLE IF EXISTS temp_hadm_filter;
CREATE TEMP TABLE temp_hadm_filter (hadm_id INTEGER PRIMARY KEY);

-- Load the hadm_id list
\copy temp_hadm_filter from 'database/hadm_id_list.txt' csv

SELECT 'Loaded ' || COUNT(*) || ' hadm_ids for filtering' AS status FROM temp_hadm_filter;

-- Create new schema for filtered data
DROP SCHEMA IF EXISTS cdm_note CASCADE;
CREATE SCHEMA cdm_note;

-----------------------------------------
-- STEP 1: Filter main note tables by hadm_id
-----------------------------------------

-- Filter discharge notes (hadm_id is NOT NULL)
CREATE TABLE cdm_note.discharge AS
SELECT d.* FROM mimiciv_note.discharge d
INNER JOIN temp_hadm_filter f ON d.hadm_id = f.hadm_id;

SELECT 'Filtered discharge: ' || COUNT(*) AS status FROM cdm_note.discharge;

-- Filter radiology notes (hadm_id can be NULL, so only keep matching ones)
CREATE TABLE cdm_note.radiology AS
SELECT r.* FROM mimiciv_note.radiology r
INNER JOIN temp_hadm_filter f ON r.hadm_id = f.hadm_id;

SELECT 'Filtered radiology: ' || COUNT(*) AS status FROM cdm_note.radiology;

-- Filter assigned radiology notes (hadm_id can be NULL, so only keep matching ones)
CREATE TABLE cdm_note.radiology_assigned AS
SELECT r.* FROM mimiciv_note.radiology_assigned r
INNER JOIN temp_hadm_filter f ON r.hadm_id = f.hadm_id;

SELECT 'Filtered radiology assigned: ' || COUNT(*) AS status FROM cdm_note.radiology_assigned;

-----------------------------------------
-- STEP 2: Filter detail tables by note_id
-----------------------------------------

-- Filter discharge_detail (references discharge note_id)
CREATE TEMP TABLE temp_discharge_note_filter AS
SELECT DISTINCT note_id FROM cdm_note.discharge;

CREATE TABLE cdm_note.discharge_detail AS
SELECT d.* FROM mimiciv_note.discharge_detail d
INNER JOIN temp_discharge_note_filter f ON d.note_id = f.note_id;

SELECT 'Filtered discharge_detail: ' || COUNT(*) AS status FROM cdm_note.discharge_detail;

-- Filter radiology_detail (references radiology note_id)
CREATE TEMP TABLE temp_radiology_note_filter AS
SELECT DISTINCT note_id FROM cdm_note.radiology;

CREATE TABLE cdm_note.radiology_detail AS
SELECT r.* FROM mimiciv_note.radiology_detail r
INNER JOIN temp_radiology_note_filter f ON r.note_id = f.note_id;

SELECT 'Filtered radiology_detail: ' || COUNT(*) AS status FROM cdm_note.radiology_detail;

-----------------------------------------
-- Summary statistics
-----------------------------------------

SELECT
    'Final Row Counts' AS info,
    (SELECT COUNT(*) FROM cdm_note.discharge) AS discharge,
    (SELECT COUNT(*) FROM cdm_note.discharge_detail) AS discharge_detail,
    (SELECT COUNT(*) FROM cdm_note.radiology) AS radiology,
    (SELECT COUNT(*) FROM cdm_note.radiology_assigned) AS radiology_assigned,
    (SELECT COUNT(*) FROM cdm_note.radiology_detail) AS radiology_detail;

SELECT 'Filtering complete! Data saved to cdm_note schema, mimiciv_note dropped' AS status;
