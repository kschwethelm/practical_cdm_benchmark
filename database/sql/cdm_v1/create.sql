-------------------------------------------
-- Create the tables and schema --
-------------------------------------------

----------------------
-- Creating schemas --
----------------------

DROP SCHEMA IF EXISTS cdm_v1 CASCADE;
CREATE SCHEMA cdm_v1;

---------------------
-- Creating tables --
---------------------

DROP TABLE IF EXISTS cdm_v1.discharge_diagnosis;
CREATE TABLE cdm_v1.discharge_diagnosis (
    hadm_id INTEGER NOT NULL,
    discharge_diagnosis TEXT NOT NULL,
    PRIMARY KEY (hadm_id)
);

DROP TABLE IF EXISTS cdm_v1.discharge_procedures;
CREATE TABLE cdm_v1.discharge_procedures (
    hadm_id INTEGER NOT NULL,
    discharge_procedure TEXT NOT NULL
);

DROP TABLE IF EXISTS cdm_v1.history_of_present_illness;
CREATE TABLE cdm_v1.history_of_present_illness (
    hadm_id INTEGER NOT NULL,
    hpi TEXT NOT NULL,
    PRIMARY KEY (hadm_id)
);

DROP TABLE IF EXISTS cdm_v1.icd_diagnosis;
CREATE TABLE cdm_v1.icd_diagnosis (
    hadm_id INTEGER NOT NULL,
    icd_diagnosis TEXT NOT NULL
);

DROP TABLE IF EXISTS cdm_v1.icd_procedures;
CREATE TABLE cdm_v1.icd_procedures (
    hadm_id INTEGER NOT NULL,
    icd_code VARCHAR(10) NOT NULL,
    icd_title TEXT NOT NULL,
    icd_version INTEGER NOT NULL
);

DROP TABLE IF EXISTS cdm_v1.laboratory_tests;
CREATE TABLE cdm_v1.laboratory_tests (
    hadm_id INTEGER NOT NULL,
    itemid INTEGER NOT NULL,
    valuestr TEXT,
    ref_range_lower NUMERIC,
    ref_range_upper NUMERIC
);

DROP TABLE IF EXISTS cdm_v1.lab_test_mapping;
CREATE TABLE cdm_v1.lab_test_mapping (
    itemid INTEGER,
    label TEXT NOT NULL,
    fluid VARCHAR(50),
    category VARCHAR(50),
    count NUMERIC,
    corresponding_ids TEXT
);

DROP TABLE IF EXISTS cdm_v1.microbiology;
CREATE TABLE cdm_v1.microbiology (
    hadm_id INTEGER NOT NULL,
    test_itemid INTEGER NOT NULL,
    valuestr TEXT,
    spec_itemid INTEGER
);

DROP TABLE IF EXISTS cdm_v1.physical_examination;
CREATE TABLE cdm_v1.physical_examination (
    hadm_id INTEGER NOT NULL,
    pe TEXT NOT NULL,
    PRIMARY KEY (hadm_id)
);

DROP TABLE IF EXISTS cdm_v1.radiology_reports;
CREATE TABLE cdm_v1.radiology_reports (
    hadm_id INTEGER NOT NULL,
    note_id VARCHAR(50) NOT NULL,
    modality VARCHAR(50),
    region VARCHAR(50),
    exam_name TEXT,
    text TEXT NOT NULL,
    PRIMARY KEY (hadm_id, note_id)
);
