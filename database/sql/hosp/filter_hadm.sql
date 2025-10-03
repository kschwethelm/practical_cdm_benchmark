-----------------------------------------
-- Filter MIMIC-IV data by hadm_id list
-- Run this AFTER assign_events.sql
-----------------------------------------
--
-- This script filters all MIMIC-IV hospital tables to only include data
-- related to the hospital admissions in the provided hadm_id list.
-- Creates a new schema 'cdm_hosp' with filtered data, then drops 'mimiciv_hosp'.
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
DROP SCHEMA IF EXISTS cdm_hosp CASCADE;
CREATE SCHEMA cdm_hosp;

-----------------------------------------
-- STEP 1: Filter base tables
-----------------------------------------

-- Filter admissions (base table with hadm_id)
CREATE TABLE cdm_hosp.admissions AS
SELECT a.* FROM mimiciv_hosp.admissions a
INNER JOIN temp_hadm_filter f ON a.hadm_id = f.hadm_id;

SELECT 'Filtered admissions: ' || COUNT(*) AS status FROM cdm_hosp.admissions;

-- Create subject_id filter from filtered admissions
CREATE TEMP TABLE temp_subject_filter AS
SELECT DISTINCT subject_id FROM cdm_hosp.admissions;

-- Filter patients (by subject_id)
CREATE TABLE cdm_hosp.patients AS
SELECT p.* FROM mimiciv_hosp.patients p
INNER JOIN temp_subject_filter s ON p.subject_id = s.subject_id;

SELECT 'Filtered patients: ' || COUNT(*) AS status FROM cdm_hosp.patients;

-----------------------------------------
-- STEP 2: Filter tables with hadm_id
-----------------------------------------

CREATE TABLE cdm_hosp.diagnoses_icd AS
SELECT d.* FROM mimiciv_hosp.diagnoses_icd d
INNER JOIN temp_hadm_filter f ON d.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.drgcodes AS
SELECT d.* FROM mimiciv_hosp.drgcodes d
INNER JOIN temp_hadm_filter f ON d.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.emar AS
SELECT e.* FROM mimiciv_hosp.emar e
INNER JOIN temp_hadm_filter f ON e.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.hcpcsevents AS
SELECT h.* FROM mimiciv_hosp.hcpcsevents h
INNER JOIN temp_hadm_filter f ON h.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.labevents AS
SELECT l.* FROM mimiciv_hosp.labevents l
INNER JOIN temp_hadm_filter f ON l.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.microbiologyevents AS
SELECT m.* FROM mimiciv_hosp.microbiologyevents m
INNER JOIN temp_hadm_filter f ON m.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.pharmacy AS
SELECT p.* FROM mimiciv_hosp.pharmacy p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.poe AS
SELECT p.* FROM mimiciv_hosp.poe p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.prescriptions AS
SELECT p.* FROM mimiciv_hosp.prescriptions p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.procedures_icd AS
SELECT p.* FROM mimiciv_hosp.procedures_icd p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.services AS
SELECT s.* FROM mimiciv_hosp.services s
INNER JOIN temp_hadm_filter f ON s.hadm_id = f.hadm_id;

CREATE TABLE cdm_hosp.transfers AS
SELECT t.* FROM mimiciv_hosp.transfers t
INNER JOIN temp_hadm_filter f ON t.hadm_id = f.hadm_id;

SELECT 'Filtered tables with hadm_id' AS status;

-----------------------------------------
-- STEP 3: Filter detail tables
-----------------------------------------

-- Filter emar_detail (references emar)
CREATE TEMP TABLE temp_emar_id_filter AS
SELECT DISTINCT emar_id FROM cdm_hosp.emar;

CREATE TABLE cdm_hosp.emar_detail AS
SELECT e.* FROM mimiciv_hosp.emar_detail e
INNER JOIN temp_emar_id_filter f ON e.emar_id = f.emar_id;

-- Filter poe_detail (references poe)
CREATE TEMP TABLE temp_poe_id_filter AS
SELECT DISTINCT poe_id FROM cdm_hosp.poe;

CREATE TABLE cdm_hosp.poe_detail AS
SELECT p.* FROM mimiciv_hosp.poe_detail p
INNER JOIN temp_poe_id_filter f ON p.poe_id = f.poe_id;

SELECT 'Filtered detail tables' AS status;

-----------------------------------------
-- STEP 4: Filter tables with subject_id only
-----------------------------------------

CREATE TABLE cdm_hosp.omr AS
SELECT o.* FROM mimiciv_hosp.omr o
INNER JOIN temp_subject_filter s ON o.subject_id = s.subject_id;

SELECT 'Filtered subject_id tables' AS status;

-----------------------------------------
-- STEP 5: Copy dictionary/reference tables
-----------------------------------------

CREATE TABLE cdm_hosp.d_hcpcs AS
SELECT * FROM mimiciv_hosp.d_hcpcs;

CREATE TABLE cdm_hosp.d_icd_diagnoses AS
SELECT * FROM mimiciv_hosp.d_icd_diagnoses;

CREATE TABLE cdm_hosp.d_icd_procedures AS
SELECT * FROM mimiciv_hosp.d_icd_procedures;

CREATE TABLE cdm_hosp.d_labitems AS
SELECT * FROM mimiciv_hosp.d_labitems;

CREATE TABLE cdm_hosp.provider AS
SELECT * FROM mimiciv_hosp.provider;

SELECT 'Copied dictionary tables' AS status;

-----------------------------------------
-- STEP 6: Drop original schema
-----------------------------------------

DROP SCHEMA mimiciv_hosp CASCADE;

SELECT 'Dropped mimiciv_hosp schema' AS status;

-----------------------------------------
-- Summary statistics
-----------------------------------------

SELECT
    'Final Row Counts' AS info,
    (SELECT COUNT(*) FROM cdm_hosp.admissions) AS admissions,
    (SELECT COUNT(*) FROM cdm_hosp.patients) AS patients,
    (SELECT COUNT(*) FROM cdm_hosp.diagnoses_icd) AS diagnoses_icd,
    (SELECT COUNT(*) FROM cdm_hosp.drgcodes) AS drgcodes,
    (SELECT COUNT(*) FROM cdm_hosp.emar) AS emar,
    (SELECT COUNT(*) FROM cdm_hosp.emar_detail) AS emar_detail,
    (SELECT COUNT(*) FROM cdm_hosp.hcpcsevents) AS hcpcsevents,
    (SELECT COUNT(*) FROM cdm_hosp.labevents) AS labevents,
    (SELECT COUNT(*) FROM cdm_hosp.microbiologyevents) AS microbiologyevents,
    (SELECT COUNT(*) FROM cdm_hosp.omr) AS omr,
    (SELECT COUNT(*) FROM cdm_hosp.pharmacy) AS pharmacy,
    (SELECT COUNT(*) FROM cdm_hosp.poe) AS poe,
    (SELECT COUNT(*) FROM cdm_hosp.poe_detail) AS poe_detail,
    (SELECT COUNT(*) FROM cdm_hosp.prescriptions) AS prescriptions,
    (SELECT COUNT(*) FROM cdm_hosp.procedures_icd) AS procedures_icd,
    (SELECT COUNT(*) FROM cdm_hosp.services) AS services,
    (SELECT COUNT(*) FROM cdm_hosp.transfers) AS transfers;

SELECT 'Filtering complete! Data saved to cdm_hosp schema, mimiciv_hosp dropped' AS status;
