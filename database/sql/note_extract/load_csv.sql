-------------------------------
-- Load data into the schema --
-------------------------------

-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -v mimic_data_dir=<PATH TO DATA DIR> -f load.sql
\cd :mimic_data_dir

-- making sure correct encoding is defined as -utf8-
SET CLIENT_ENCODING TO 'utf8';

\COPY cdm_note_extract.admissions FROM 'admissions.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.allergies FROM 'allergies.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.chief_complaint FROM 'chief_complaint.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.procedures FROM 'procedures.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.past_medical_history FROM 'past_medical_history.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.physical_exam FROM 'physical_exam.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.discharge_diagnosis FROM 'discharge_diagnosis.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_note_extract.discharge_free_text FROM 'discharge_free_text.csv' DELIMITER ',' CSV HEADER NULL '';
