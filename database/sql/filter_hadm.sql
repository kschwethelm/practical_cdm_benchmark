-----------------------------------------
-- Filter MIMIC-IV data by hadm_id list
-- Run this AFTER assign_events.sql
-----------------------------------------
--
-- This script filters all MIMIC-IV tables to only include data
-- related to the hospital admissions in the provided hadm_id list.
--
-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -v hadm_list=<PATH TO hadm_id_list.txt> -f filter_hadm.sql

SET CLIENT_ENCODING TO 'utf8';

-- Create temporary table for hadm_id filtering
DROP TABLE IF EXISTS temp_hadm_filter;
CREATE TEMP TABLE temp_hadm_filter (hadm_id INTEGER PRIMARY KEY);

-- Load the hadm_id list using client-side copy via PROGRAM
\copy temp_hadm_filter from 'database/hadm_id_list.txt' csv

SELECT 'Loaded ' || COUNT(*) || ' hadm_ids for filtering' AS status FROM temp_hadm_filter;

-- Create filtered versions of tables in a new schema
DROP SCHEMA IF EXISTS mimiciv_filtered CASCADE;
CREATE SCHEMA mimiciv_filtered;

-- Filter admissions (base table)
CREATE TABLE mimiciv_filtered.admissions AS
SELECT a.* FROM mimiciv_hosp.admissions a
INNER JOIN temp_hadm_filter f ON a.hadm_id = f.hadm_id;

SELECT 'Filtered admissions: ' || COUNT(*) AS status FROM mimiciv_filtered.admissions;

-- Create subject_id filter from filtered admissions
CREATE TEMP TABLE temp_subject_filter AS
SELECT DISTINCT subject_id FROM mimiciv_filtered.admissions;

-- Filter patients (by subject_id)
CREATE TABLE mimiciv_filtered.patients AS
SELECT p.* FROM mimiciv_hosp.patients p
INNER JOIN temp_subject_filter s ON p.subject_id = s.subject_id;

SELECT 'Filtered patients: ' || COUNT(*) AS status FROM mimiciv_filtered.patients;

-- Filter tables with hadm_id
CREATE TABLE mimiciv_filtered.diagnoses_icd AS
SELECT d.* FROM mimiciv_hosp.diagnoses_icd d
INNER JOIN temp_hadm_filter f ON d.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.drgcodes AS
SELECT d.* FROM mimiciv_hosp.drgcodes d
INNER JOIN temp_hadm_filter f ON d.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.emar AS
SELECT e.* FROM mimiciv_hosp.emar e
INNER JOIN temp_hadm_filter f ON e.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.hcpcsevents AS
SELECT h.* FROM mimiciv_hosp.hcpcsevents h
INNER JOIN temp_hadm_filter f ON h.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.labevents AS
SELECT l.* FROM mimiciv_hosp.labevents l
INNER JOIN temp_hadm_filter f ON l.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.microbiologyevents AS
SELECT m.* FROM mimiciv_hosp.microbiologyevents m
INNER JOIN temp_hadm_filter f ON m.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.pharmacy AS
SELECT p.* FROM mimiciv_hosp.pharmacy p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.poe AS
SELECT p.* FROM mimiciv_hosp.poe p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.prescriptions AS
SELECT p.* FROM mimiciv_hosp.prescriptions p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.procedures_icd AS
SELECT p.* FROM mimiciv_hosp.procedures_icd p
INNER JOIN temp_hadm_filter f ON p.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.services AS
SELECT s.* FROM mimiciv_hosp.services s
INNER JOIN temp_hadm_filter f ON s.hadm_id = f.hadm_id;

CREATE TABLE mimiciv_filtered.transfers AS
SELECT t.* FROM mimiciv_hosp.transfers t
INNER JOIN temp_hadm_filter f ON t.hadm_id = f.hadm_id;

SELECT 'Filtered hosp tables with hadm_id' AS status;

-- Filter detail tables (no hadm_id, use parent table keys)
CREATE TEMP TABLE temp_emar_id_filter AS
SELECT DISTINCT emar_id FROM mimiciv_filtered.emar;

CREATE TABLE mimiciv_filtered.emar_detail AS
SELECT e.* FROM mimiciv_hosp.emar_detail e
INNER JOIN temp_emar_id_filter f ON e.emar_id = f.emar_id;

CREATE TEMP TABLE temp_poe_id_filter AS
SELECT DISTINCT poe_id FROM mimiciv_filtered.poe;

CREATE TABLE mimiciv_filtered.poe_detail AS
SELECT p.* FROM mimiciv_hosp.poe_detail p
INNER JOIN temp_poe_id_filter f ON p.poe_id = f.poe_id;

SELECT 'Filtered detail tables' AS status;

-- Filter tables with subject_id only
CREATE TABLE mimiciv_filtered.omr AS
SELECT o.* FROM mimiciv_hosp.omr o
INNER JOIN temp_subject_filter s ON o.subject_id = s.subject_id;

SELECT 'Filtered subject_id tables' AS status;

-- Copy dictionary/lookup tables (no filtering needed)
CREATE TABLE mimiciv_filtered.d_hcpcs AS SELECT * FROM mimiciv_hosp.d_hcpcs;
CREATE TABLE mimiciv_filtered.d_icd_diagnoses AS SELECT * FROM mimiciv_hosp.d_icd_diagnoses;
CREATE TABLE mimiciv_filtered.d_icd_procedures AS SELECT * FROM mimiciv_hosp.d_icd_procedures;
CREATE TABLE mimiciv_filtered.d_labitems AS SELECT * FROM mimiciv_hosp.d_labitems;
CREATE TABLE mimiciv_filtered.provider AS SELECT * FROM mimiciv_hosp.provider;

SELECT 'Copied dictionary tables' AS status;

-- Filter ICU tables
CREATE TABLE mimiciv_filtered.icustays AS
SELECT i.* FROM mimiciv_icu.icustays i
INNER JOIN temp_hadm_filter f ON i.hadm_id = f.hadm_id;

SELECT 'Filtered icustays: ' || COUNT(*) AS status FROM mimiciv_filtered.icustays;

-- Create stay_id filter from filtered icustays
CREATE TEMP TABLE temp_stay_filter AS
SELECT DISTINCT stay_id FROM mimiciv_filtered.icustays;

CREATE TABLE mimiciv_filtered.chartevents AS
SELECT c.* FROM mimiciv_icu.chartevents c
INNER JOIN temp_stay_filter s ON c.stay_id = s.stay_id;

CREATE TABLE mimiciv_filtered.datetimeevents AS
SELECT d.* FROM mimiciv_icu.datetimeevents d
INNER JOIN temp_stay_filter s ON d.stay_id = s.stay_id;

CREATE TABLE mimiciv_filtered.ingredientevents AS
SELECT i.* FROM mimiciv_icu.ingredientevents i
INNER JOIN temp_stay_filter s ON i.stay_id = s.stay_id;

CREATE TABLE mimiciv_filtered.inputevents AS
SELECT i.* FROM mimiciv_icu.inputevents i
INNER JOIN temp_stay_filter s ON i.stay_id = s.stay_id;

CREATE TABLE mimiciv_filtered.outputevents AS
SELECT o.* FROM mimiciv_icu.outputevents o
INNER JOIN temp_stay_filter s ON o.stay_id = s.stay_id;

CREATE TABLE mimiciv_filtered.procedureevents AS
SELECT p.* FROM mimiciv_icu.procedureevents p
INNER JOIN temp_stay_filter s ON p.stay_id = s.stay_id;

SELECT 'Filtered ICU event tables' AS status;

-- Copy ICU dictionary tables
CREATE TABLE mimiciv_filtered.d_items AS SELECT * FROM mimiciv_icu.d_items;
CREATE TABLE mimiciv_filtered.caregiver AS SELECT * FROM mimiciv_icu.caregiver;

SELECT 'Copied ICU dictionary tables' AS status;

-- Summary statistics
SELECT
    'Summary' AS info,
    (SELECT COUNT(*) FROM mimiciv_filtered.admissions) AS admissions,
    (SELECT COUNT(*) FROM mimiciv_filtered.patients) AS patients,
    (SELECT COUNT(*) FROM mimiciv_filtered.labevents) AS labevents,
    (SELECT COUNT(*) FROM mimiciv_filtered.microbiologyevents) AS microbiologyevents,
    (SELECT COUNT(*) FROM mimiciv_filtered.icustays) AS icustays,
    (SELECT COUNT(*) FROM mimiciv_filtered.chartevents) AS chartevents;

SELECT 'Filtering complete! Data saved to mimiciv_filtered schema' AS status;