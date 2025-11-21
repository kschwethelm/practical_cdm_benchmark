-------------------------------------------
-- Create the tables and schema --
-------------------------------------------

----------------------
-- Creating schemas --
----------------------

DROP SCHEMA IF EXISTS cdm_note_extract CASCADE;
CREATE SCHEMA cdm_note_extract;

---------------------
-- Creating tables --
---------------------

DROP TABLE IF EXISTS cdm_note_extract.admissions;
CREATE TABLE cdm_note_extract.admissions (
    hadm_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    note_id VARCHAR(25) NOT NULL,
    gender VARCHAR(1) NOT NULL,
    service_type VARCHAR(25) NOT NULL,
    discharge_disposition VARCHAR(20),
    PRIMARY KEY (hadm_id)
);

DROP TABLE IF EXISTS cdm_note_extract.discharge_diagnosis;
CREATE TABLE cdm_note_extract.discharge_diagnosis (
    hadm_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL,
    seq_num INTEGER NOT NULL,
    PRIMARY KEY (hadm_id, seq_num)
);

DROP TABLE IF EXISTS cdm_note_extract.allergies;
CREATE TABLE cdm_note_extract.allergies (
    hadm_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    PRIMARY KEY (hadm_id, title)
);

DROP TABLE IF EXISTS cdm_note_extract.chief_complaint;
CREATE TABLE cdm_note_extract.chief_complaint (
    hadm_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL, -- 'chief_complaint', 'circumstances'
    complaint TEXT NOT NULL,
    seq_num INTEGER NOT NULL,
    PRIMARY KEY (hadm_id, category, seq_num)
);

DROP TABLE IF EXISTS cdm_note_extract.procedures;
CREATE TABLE cdm_note_extract.procedures (
    hadm_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    is_previous BOOLEAN NOT NULL,
    seq_num INTEGER NOT NULL,
    PRIMARY KEY (hadm_id, seq_num)
);

--DROP TABLE IF EXISTS cdm_note_extract.past_medical_history;
--CREATE TABLE cdm_note_extract.past_medical_history (
--    hadm_id INTEGER NOT NULL,
--    title TEXT NOT NULL,
--    category VARCHAR(20) NOT NULL, -- 'medical', 'surgical', 'cardiac', 'oncologic', 'psychiatric', 'gynecologic', 'family', 'social', 'other'
--    seq_num INTEGER NOT NULL,
--    PRIMARY KEY (hadm_id, category, seq_num)
--);

--DROP TABLE IF EXISTS cdm_note_extract.physical_exam;
--CREATE TABLE cdm_note_extract.physical_exam (
--    hadm_id INTEGER NOT NULL,
--    temporal_context VARCHAR(20),
--    vital_signs TEXT,
--    general TEXT,
--    heent_neck TEXT,
--    cardiovascular TEXT,
--    pulmonary TEXT,
--    abdominal TEXT,
--    extremities TEXT,
--    skin TEXT,
--    neurological TEXT,
--    musculoskeletal TEXT,
--    genitourinary TEXT,
--    lymphatic TEXT,
--    access TEXT,
--    psychiatric TEXT,
--    pain TEXT,
--    orthostatics TEXT,
--    other TEXT
--);

DROP TABLE IF EXISTS cdm_note_extract.discharge_free_text;
CREATE TABLE cdm_note_extract.discharge_free_text (
    hadm_id INTEGER NOT NULL,
    allergies TEXT,
    chief_complaint TEXT,
    discharge_diagnosis TEXT,
    discharge_condition TEXT,
    discharge_medications TEXT,
    major_procedure TEXT,
    medications_on_admission TEXT,
    pertinent_results TEXT,
    physical_examination TEXT,
    past_medical_history TEXT,
    history_of_present_illness TEXT,
    brief_hospital_course TEXT,
    discharge_instructions TEXT,
    PRIMARY KEY (hadm_id)
);
