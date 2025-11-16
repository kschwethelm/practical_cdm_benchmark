-------------------------------
-- Load data into the schema --
-------------------------------

-- To run from a terminal:
--  psql "dbname=<DBNAME> user=<USER>" -v mimic_data_dir=<PATH TO DATA DIR> -f load_csv.sql
\cd :mimic_data_dir

-- making sure correct encoding is defined as -utf8-
SET CLIENT_ENCODING TO 'utf8';

\COPY cdm_v1.discharge_diagnosis FROM 'discharge_diagnosis.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.discharge_procedures FROM 'discharge_procedures.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.history_of_present_illness FROM 'history_of_present_illness.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.icd_diagnosis FROM 'icd_diagnosis.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.icd_procedures FROM 'icd_procedures.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.laboratory_tests FROM 'laboratory_tests.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.lab_test_mapping FROM 'lab_test_mapping.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.microbiology FROM 'microbiology.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.physical_examination FROM 'physical_examination.csv' DELIMITER ',' CSV HEADER NULL '';
\COPY cdm_v1.radiology_reports FROM 'radiology_reports.csv' DELIMITER ',' CSV HEADER NULL '';
