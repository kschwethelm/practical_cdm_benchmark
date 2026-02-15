# CDM Benchmark Dataset Specification

This document describes the specifications for the replication of our benchmark dataset of **CDMv1**. The dataset provides a baseline for evaluating clinical decision-making pipelines

## Create Benchmark Dataset

For a total of n admissions:
   ```bash
   uv run database/create_benchmark.py num_cases=n
   ```

For all admissions:
   ```bash
   uv run database/create_benchmark.py
   ```

For getting a maximum of 3 tests (lab, microbiology and radiology results), which were performed before the first treatment:
   ```bash
   uv run database/create_benchmark.py extended=true
   ```

---

## Data Overview

| Data Field               | Source Table                                   | Purpose in Benchmark                   |
|--------------------------|-------------------------------------------------|-----------------------------------------|
| **hadm_id**              | `cdm_hosp.admissions.hadm_id`                           | Unique Identifier & Reproducibility    |
| **history_of_present_illness** | `cdm_note_extract.discharge_free_text`     | LLM Input (Prompt)                     |
| **physical_exams**       | `cdm_note_extract.discharge_free_text`                | Tool Output (Physical Exam)            |
| **lab_results**          | `cdm_hosp.labevents`, `cdm_hosp.d_labitems`       | Tool Output (Labs)                     |
| **microbiology_events**    | `cdm_hosp.microbiologyevents`                            | Tool Output (Labs)               |
| **radiology_reports**    | `cdm_note.radiology`, `cdm_note.radiology_detail`                            | Tool Output (Imaging)                  |
| **ground_truth**         | `cdm_note_extract.discharge_diagnosis`, `cdm_hosp.procedures_icd`, `cdm_hosp.d_icd_procedures`, `cdm_note_extract.procedures`          | Evaluation          |
| **demographics**         | `cdm_hosp.patients`                             | Analysis                  |

---

## Detailed Field Specifications

### 1. Case Identification
**Data Field:** `hadm_id`\
**Source:** `cdm_hosp.admissions.hadm_id`

**Why?:**
Primary key linking all tables (notes, labs, imaging). Ensures each case is traceable to the original MIMIC-IV data.

---

### 2. Initial Patient Context (Prompt Input)
**Data Field:** `history_of_present_illness`\
**Source:** `cdm_note_extract.discharge_free_text.history_of_present_illness`\
**Processing:**
- Apply `utils.scrub_text` to remove diagnostic leakage.

**Why?:**
Simulates the initial patient presentation. Provides context **without revealing the diagnosis**.

---

### 3. Physical Examination
**Data Field:** `physical_exams`\
**Source:** `cdm_note_extract.discharge_free_text`\
**Processing:**
- Scrub diagnostic terms.

**Why?:**
Serves as output for the `physical_examination` tool. Provides objective findings and is an essential
part of the diagnostic process (preferably first action).

---

### 4. Laboratory & Microbiology Results
**Data Field:** `lab_results`, `microbiology_event`\
**Sources:**
- **Labs:** `cdm_hosp.labevents`, `cdm_hosp.d_labitems`
  (test_name, value, unit, ref_range_lower, ref_range_upper, flag, sequence_num)
- **Microbiology:** `cdm_hosp.microbiologyevents`
  (test_name, spec_type_desc, organism_name, comments, charttime, sequence_num)

**Processing:**
- Keep **up to 3 results per test type**
- Only include tests where `charttime < first_procedure_time` from `cdm_hosp.procedures_icd.chartdate`.
- If no procedures exist, include all tests up to the maximum.
- Each result includes `sequence_num` indicating which occurrence (1, 2, or 3).

**Why?:**
Output for `request_lab_test`.
Lab values capture inflammation/organ dysfunction; cultures reveal infectious causes.
Multiple results allow tracking progression before treatment.

---

### 5. Radiology Reports
**Data Field:** `radiology_reports`\
**Source:** `cdm_note.radiology`, `cdm_note.radiology_detail`\
**Metadata:**
- Modality & Region derived from `cdm_note.radiology_detail.exam_name`
- `sequence_num` indicating which occurrence of each report (1, 2, or 3)

**Processing (Critical):**
1. Extract only the **FINDINGS** section.
2. **Remove the IMPRESSION and other negative sections** (contain diagnostic conclusions).
3. Scrub diagnostic keywords from findings.
4. Keep **up to 3 reports per note_id** where `charttime < first_procedure_time`.
5. Skip reports with Unknown modality or region.

**Why?:**
Output for `request_imaging`.
Forces the LLM to interpret imaging findings instead of reading the radiologist's diagnosis.
Multiple reports show progression before treatment.

---

### 6. Ground Truth (Evaluation Only)
**Data Field:** `ground_truth`
- **Primary Diagnosis:** `cdm_note_extract.discharge_diagnosis` (where `is_primary = True`)
- **Treatments:** From `cdm_hosp.procedures_icd, cdm_hosp.d_icd_procedures` (coded) and `cdm_note_extract.procedures` (free text)

**Why?:**
Serves as the **answer key**.
Never shown to the LLM; used exclusively by evaluation scripts.

---

### 7. Demographics (Analysis Only)
**Data Field:** `demographics`
- **Age:** Derived from `cdm_hosp.patients.anchor_age`
- **Gender:** `cdm_hosp.patients.gender`

**Why?:**
Used only for **post-hoc bias analysis**.
Not provided to the LLM to prevent performance skew.
