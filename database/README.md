# MIMIC-IV Database Overview

This database contains a filtered subset of the MIMIC-IV clinical database, focusing on **2,333 hospital admissions** selected for the clinical decision-making benchmark.

## Database Schemas

The database is organized into three main schemas:

1. **`cdm_hosp`** - Hospital data (demographics, diagnoses, medications, labs, etc.)
2. **`cdm_note`** - Clinical notes (discharge summaries, radiology reports)
3. **`cdm_note_extract`** - Structured extractions from discharge notes

---

## 1. Hospital Schema (`cdm_hosp`)

Contains 22 tables with hospital admission data. All tables are filtered to only include data from the 2,333 selected admissions.

### Core Tables

#### `admissions` (2,333 rows)
Primary admission records with demographic and administrative information.
- **Key columns**: `hadm_id`, `subject_id`, `admittime`, `dischtime`, `deathtime`, `admission_type`, `discharge_location`, `insurance`, `race`, `hospital_expire_flag`
- **Primary key**: `hadm_id` (hospital admission ID)

#### `patients` (2,320 rows)
Patient demographics. Note: fewer patients than admissions because some patients have multiple admissions.
- **Key columns**: `subject_id`, `gender`, `anchor_age`, `anchor_year`, `dod` (date of death)
- **Primary key**: `subject_id`

### Diagnosis & Procedure Tables

#### `diagnoses_icd` (16,363 rows)
ICD-coded diagnoses for each admission.
- **Key columns**: `hadm_id`, `seq_num`, `icd_code`, `icd_version`
- Use with `d_icd_diagnoses` dictionary table for descriptions

#### `procedures_icd` (2,655 rows)
ICD-coded procedures performed during admission.
- **Key columns**: `hadm_id`, `seq_num`, `icd_code`, `icd_version`, `chartdate`
- Use with `d_icd_procedures` dictionary table for descriptions

#### `drgcodes` (3,131 rows)
Diagnosis-Related Group (DRG) codes for billing.
- **Key columns**: `hadm_id`, `drg_code`, `description`, `drg_severity`, `drg_mortality`

### Laboratory & Microbiology Tables

#### `labevents` (246,177 rows)
Laboratory test results (blood tests, chemistry, hematology, etc.).
- **Key columns**: `hadm_id`, `itemid`, `charttime`, `value`, `valuenum`, `valueuom`, `flag`, `ref_range_lower`, `ref_range_upper`
- Use with `d_labitems` dictionary table to decode `itemid`
- **Note**: May include events assigned to admissions based on timing (see `assign_events.sql`)

#### `microbiologyevents` (5,177 rows)
Microbiology cultures and antibiotic sensitivity results.
- **Key columns**: `hadm_id`, `charttime`, `spec_type_desc`, `test_name`, `org_name`, `ab_name`, `interpretation`
- **Note**: May include events assigned to admissions based on timing

### Medication Tables

#### `prescriptions` (71,328 rows)
Medication prescriptions during admission.
- **Key columns**: `hadm_id`, `drug`, `drug_type`, `starttime`, `stoptime`, `dose_val_rx`, `dose_unit_rx`, `route`

#### `pharmacy` (62,066 rows)
Pharmacy orders and medication dispensing.
- **Key columns**: `hadm_id`, `medication`, `starttime`, `stoptime`, `route`, `frequency`, `status`

#### `emar` (100,759 rows)
Electronic Medication Administration Records - when medications were actually given.
- **Key columns**: `hadm_id`, `emar_id`, `charttime`, `medication`, `event_txt`

#### `emar_detail` (198,997 rows)
Detailed administration information for each EMAR record.
- **Key columns**: `emar_id`, `dose_given`, `dose_given_unit`, `route`, `site`, `infusion_rate`
- **Foreign key**: Links to `emar` via `emar_id`

### Provider Orders

#### `poe` (192,821 rows)
Provider Order Entry - all orders placed by clinicians.
- **Key columns**: `hadm_id`, `poe_id`, `ordertime`, `order_type`, `order_subtype`, `order_status`

#### `poe_detail` (20,183 rows)
Detailed information about provider orders.
- **Key columns**: `poe_id`, `field_name`, `field_value`
- **Foreign key**: Links to `poe` via `poe_id`

### Other Clinical Tables

#### `hcpcsevents` (1,010 rows)
HCPCS procedures (outpatient procedures, supplies, services).
- **Key columns**: `hadm_id`, `hcpcs_cd`, `chartdate`, `short_description`
- Use with `d_hcpcs` dictionary table

#### `services` (2,546 rows)
Hospital service transfers (e.g., Medicine → Surgery).
- **Key columns**: `hadm_id`, `transfertime`, `prev_service`, `curr_service`

#### `transfers` (8,853 rows)
Physical location transfers within the hospital.
- **Key columns**: `hadm_id`, `transfer_id`, `eventtype`, `careunit`, `intime`, `outtime`

#### `omr` (116,823 rows)
Outpatient Medical Records - measurements like height, weight, BMI.
- **Key columns**: `subject_id`, `chartdate`, `result_name`, `result_value`
- **Note**: Linked by `subject_id` only, not `hadm_id`

### Dictionary/Reference Tables

These tables contain full data (not filtered) to decode IDs and codes:

- **`d_hcpcs`** - HCPCS code descriptions
- **`d_icd_diagnoses`** - ICD diagnosis descriptions (versions 9 and 10)
- **`d_icd_procedures`** - ICD procedure descriptions (versions 9 and 10)
- **`d_labitems`** - Laboratory test item descriptions
- **`provider`** - Provider IDs

---

## 2. Note Schema (`cdm_note`)

Contains clinical text notes for the 2,333 admissions.

### `discharge` (2,333 rows)
Discharge summaries - comprehensive narratives written when patients leave the hospital.
- **Key columns**: `note_id`, `hadm_id`, `subject_id`, `note_type`, `charttime`, `text`
- One discharge note per admission

### `discharge_detail` (1,289 rows)
Structured fields extracted from discharge notes.
- **Key columns**: `note_id`, `field_name`, `field_value`, `field_ordinal`
- **Foreign key**: Links to `discharge` via `note_id`

### `radiology` (5,411 rows)
Radiology reports (X-rays, CT scans, MRIs, ultrasounds, etc.).
- **Key columns**: `note_id`, `hadm_id`, `subject_id`, `note_type`, `charttime`, `text`
- Multiple radiology reports per admission (average ~2.3 per admission)

### `radiology_detail` (13,156 rows)
Structured fields from radiology reports.
- **Key columns**: `note_id`, `field_name`, `field_value`, `field_ordinal`
- **Foreign key**: Links to `radiology` via `note_id`

---

## 3. Note Extract Schema (`cdm_note_extract`)

Structured information extracted from discharge notes using LLMs (work in progress).

### `admissions` (Primary table)
Core admission information from discharge notes.
- **Key columns**: `hadm_id`, `subject_id`, `note_id`, `gender`, `service_type`, `discharge_disposition`

### `discharge_diagnosis`
Discharge diagnoses as written in notes (not ICD codes, more accurate descriptions).
- **Key columns**: `hadm_id`, `title`, `is_primary`, `seq_num`
- Multiple diagnoses per admission

### `allergies`
Patient allergies documented in notes.
- **Key columns**: `hadm_id`, `title`
- Multiple allergies possible per admission

### `chief_complaint`
Reason for hospital visit from patient perspective.
- **Key columns**: `hadm_id`, `category`, `complaint`, `seq_num`
- **Categories**: `chief_complaint`, `circumstances`, `patient_quote`

### `procedures`
Procedures performed during hospitalization.
- **Key columns**: `hadm_id`, `title`, `is_previous`, `seq_num`
- **`is_previous`**: Boolean - true if procedure was before admission

### `past_medical_history`
Patient's medical history before admission.
- **Key columns**: `hadm_id`, `title`, `category`, `seq_num`
- **Categories**: `medical`, `surgical`, `cardiac`, `oncologic`, `psychiatric`, `gynecologic`, `family`, `social`, `other`

### `physical_exam`
Physical examination findings at different time points.
- **Key columns**: `hadm_id`, `temporal_context`, `vital_signs`, `general`, `heent_neck`, `cardiovascular`, `pulmonary`, `abdominal`, `extremities`, `neurological`, `skin`, etc.
- Organized by body system

### `discharge_free_text`
Unchanged free-text sections from discharge notes.
- **Key columns**: `hadm_id`, `allergies`, `chief_complaint`, `discharge_diagnosis`, `discharge_condition`, `discharge_medications`, `major_procedure`, `medications_on_admission`, `pertinent_results`, `physical_examination`, `past_medical_history`, `history_of_present_illness`, `brief_hospital_course`, `discharge_instructions`
- Unstructured text fields

---

## Key Relationships

The main table relationships are:

```
patients (subject_id) --+-> admissions (hadm_id) --+-> diagnoses_icd
                        |                          +-> procedures_icd
                        |                          +-> prescriptions
                        |                          +-> labevents
                        |                          +-> discharge notes
                        |                          +-> ...
                        |
                        +-> omr (outpatient data, no hadm_id)

discharge (note_id) --> discharge_detail
radiology (note_id) --> radiology_detail
emar (emar_id) --> emar_detail
poe (poe_id) --> poe_detail
```

---

## Data Filtering Notes

- All `cdm_hosp` and `cdm_note` tables are filtered to only include data from admissions in `database/hadm_id_list.txt`
- Lab and microbiology events may have been assigned to admissions based on timing (see `assign_events.sql`)
- Dictionary tables (prefix `d_`) contain complete reference data for code lookups
- Total admissions: **2,333** across **2,320** unique patients

---

## Useful Queries

### Get patient demographics for an admission
```sql
SELECT p.gender, p.anchor_age, a.race, a.insurance, a.admission_type
FROM cdm_hosp.admissions a
JOIN cdm_hosp.patients p ON a.subject_id = p.subject_id
WHERE a.hadm_id = 20000602;
```

### Get all ICD diagnoses with descriptions
```sql
SELECT d.icd_code, d.icd_version, dict.long_title, d.seq_num
FROM cdm_hosp.diagnoses_icd d
LEFT JOIN cdm_hosp.d_icd_diagnoses dict
  ON d.icd_code = dict.icd_code AND d.icd_version = dict.icd_version
WHERE d.hadm_id = 20000602
ORDER BY d.seq_num;
```

### Get discharge summary text
```sql
SELECT text
FROM cdm_note.discharge
WHERE hadm_id = 20000602;
```

### Get structured chief complaint
```sql
SELECT category, complaint
FROM cdm_note_extract.chief_complaint
WHERE hadm_id = 20000602
ORDER BY seq_num;
```

---

## Additional Resources

- [MIMIC-IV Documentation](https://mimic.mit.edu/docs/iv/modules/hosp/)
- [MIMIC-IV-Note Documentation](https://mimic.mit.edu/docs/iv/modules/note/)
- Column definitions and detailed schema: See table creation scripts in this directory

## Appendix

### Create Database from Scratch (not needed for you)

Follow these steps to set up the database on a local machine.

#### Install PostgreSQL

Steps for Ubuntu:

1. Install PostgreSQL:
   ```bash
   sudo apt install postgresql
   ```

2. Create database:
   Go into psql shell:
      ```bash
      sudo -u postgres psql
      ```

   Within psql shell:
      ```sql
      CREATE DATABASE mimiciv_pract;
      -- Create admin user with password
      CREATE ROLE admin_user WITH LOGIN PASSWORD 'YourStrongPassword';
      ALTER ROLE admin_user WITH SUPERUSER CREATEDB CREATEROLE;
      -- Create student user with basic rights
      CREATE ROLE student WITH LOGIN PASSWORD 'student';
      GRANT ALL PRIVILEGES ON DATABASE mimiciv_pract TO student;
      -- To grant read access to specific (existing schemas and tables)
      GRANT USAGE ON SCHEMA cdm_hosp TO student;
      GRANT SELECT ON ALL TABLES IN SCHEMA cdm_hosp TO student;
      GRANT USAGE ON SCHEMA cdm_note TO student;
      GRANT SELECT ON ALL TABLES IN SCHEMA cdm_note TO student;
      GRANT USAGE ON SCHEMA cdm_note_extract TO student;
      GRANT SELECT ON ALL TABLES IN SCHEMA cdm_note_extract TO student;
      ```

3. Test access:
   Go into psql shell
      ```bash
      psql -U student -d mimiciv_pract -h localhost
      ```

   Run test query:
      ```sql
      SELECT hadm_id, subject_id, admittime FROM cdm_hosp.admissions LIMIT 5;
      ```

#### Create MIMIC Database

1. Download MIMIC-IV hosp `*.csv.gz` files from https://physionet.org/content/mimiciv/3.1/

2. Load and filter hosp module:

   ```bash
   MIMIC_DIR=/srv/mimic/mimiciv/3.1/

   # Create (empty) tables
   psql -d mimiciv_pract -f database/sql/hosp/create.sql

   # Load data into tables
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$MIMIC_DIR -f database/sql/hosp/load_gz.sql

   # Set primary keys, indexes, etc.
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/constraint.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/index.sql

   # Assign lab and microbiology events to hadm_id based on time (optional)
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/assign_events.sql

   # Remove admissions not in 'database/hadm_id_list.txt'
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/filter_hadm.sql
   ```

3. Load and filter note module:
   ```bash
   MIMIC_DIR=/srv/mimic/mimiciv/mimic-iv-note/2.2/note/
   psql -d mimiciv_pract -f database/sql/note/create.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$MIMIC_DIR -f database/sql/note/load_gz.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/note/filter_hadm.sql
   ```

4. Load note extractions:

   ```bash
   EXTRACT_DIR=/home/$USER/practical_cdm_benchmark/database/data
   psql -d mimiciv_pract -f database/sql/note_extract/create.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$EXTRACT_DIR -f database/sql/note_extract/load_csv.sql
   ```
