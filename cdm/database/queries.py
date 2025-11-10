import psycopg
from loguru import logger
from cdm.database.utils import *


def get_demographics(cursor: psycopg.Cursor, hadm_id: int) -> dict | None:
    """
    Get patient demographics for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        dict with 'age' and 'gender', or None if not found
    """
    query = """
        SELECT p.anchor_age, p.gender
        FROM cdm_hosp.admissions a
        JOIN cdm_hosp.patients p ON a.subject_id = p.subject_id
        WHERE a.hadm_id = %s
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return {"age": result[0], "gender": result[1]}
    logger.warning(f"No demographics found for hadm_id={hadm_id}")
    return None


def get_first_lab_result(cursor: psycopg.Cursor, hadm_id: int) -> dict | None:
    """
    Get the first lab result (by charttime) for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        dict with lab result details, or None if not found
    """
    query = """
        SELECT itemid, charttime, value, valuenum, valueuom
        FROM cdm_hosp.labevents
        WHERE hadm_id = %s
        ORDER BY charttime ASC
        LIMIT 1
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return {
            "itemid": result[0],
            "charttime": result[1],
            "value": result[2],
            "valuenum": result[3],
            "valueuom": result[4],
        }
    logger.debug(f"No lab results found for hadm_id={hadm_id}")
    return None


def get_first_microbiology_result(cursor: psycopg.Cursor, hadm_id: int) -> dict | None:
    """
    Get the first microbiology result (by charttime) for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        dict with microbiology result details, or None if not found
    """
    query = """
        SELECT charttime, spec_type_desc, test_name, org_name, interpretation
        FROM cdm_hosp.microbiologyevents
        WHERE hadm_id = %s
        ORDER BY charttime ASC
        LIMIT 1
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return {
            "charttime": result[0],
            "spec_type_desc": result[1],
            "test_name": result[2],
            "org_name": result[3],
            "interpretation": result[4],
        }
    logger.debug(f"No microbiology results found for hadm_id={hadm_id}")
    return None


def get_presenting_chief_complaints(cursor: psycopg.Cursor, hadm_id: int) -> list[str]:
    """
    Get all chief complaints with category='chief_complaint' for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of complaint strings (may be empty)
    """
    query = """
        SELECT complaint
        FROM cdm_note_extract.chief_complaint
        WHERE hadm_id = %s AND category = 'chief_complaint'
        ORDER BY seq_num
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    complaints = [row[0] for row in results if row[0]]
    logger.debug(f"Found {len(complaints)} presenting complaints for hadm_id={hadm_id}")
    return complaints


def get_first_diagnosis(cursor: psycopg.Cursor, hadm_id: int) -> str | None:
    """
    Get the first primary discharge diagnosis for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        Diagnosis title string, or None if not found
    """
    query = """
        SELECT title
        FROM cdm_note_extract.discharge_diagnosis
        WHERE hadm_id = %s AND is_primary = true
        ORDER BY seq_num
        LIMIT 1
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    logger.debug(f"No primary diagnosis found for hadm_id={hadm_id}")
    return None


def get_all_past_medical_history(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get all past medical history entries for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with 'note' and 'category' (may be empty)
    """
    query = """
        SELECT title, category
        FROM cdm_note_extract.past_medical_history
        WHERE hadm_id = %s
        ORDER BY seq_num
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    history = [{"note": row[0], "category": row[1]} for row in results if row[0]]
    logger.debug(f"Found {len(history)} past medical history entries for hadm_id={hadm_id}")
    return history


def get_first_physical_exam(cursor: psycopg.Cursor, hadm_id: int) -> dict | None:
    """
    Get the first physical examination entry for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        dict with physical exam fields, or None if not found
    """
    query = """
        SELECT temporal_context, vital_signs, general, heent_neck, cardiovascular,
               pulmonary, abdominal, extremities, neurological, skin
        FROM cdm_note_extract.physical_exam
        WHERE hadm_id = %s
        LIMIT 1
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return {
            "temporal_context": result[0],
            "vital_signs": result[1],
            "general": result[2],
            "heent_neck": result[3],
            "cardiovascular": result[4],
            "pulmonary": result[5],
            "abdominal": result[6],
            "extremities": result[7],
            "neurological": result[8],
            "skin": result[9],
        }
    logger.debug(f"No physical exam found for hadm_id={hadm_id}")
    return None


def get_history_of_present_illness(cursor: psycopg.Cursor, hadm_id: int) -> str | None:
    """
    Get the history of present illness for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        History of present illness string, or None if not found
    """
    query = """
        SELECT history_of_present_illness
        FROM cdm_note_extract.discharge_free_text
        WHERE hadm_id = %s
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    logger.debug(f"No history of present illness found for hadm_id={hadm_id}")
    return None


def get_physical_examination(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get structured physical examination findings for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with physical exam fields (may be empty)
    """
    query = """
        SELECT
            temporal_context,
            vital_signs,
            general,
            heent_neck,
            cardiovascular,
            pulmonary,
            abdominal,
            extremities,
            neurological,
            skin
        FROM cdm_note_extract.physical_exam
        WHERE hadm_id = %s
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    exams = [
        {
            "temporal_context": row[0],
            "vital_signs": row[1],
            "general": row[2],
            "heent_neck": row[3],
            "cardiovascular": row[4],
            "pulmonary": row[5],
            "abdominal": row[6],
            "extremities": row[7],
            "neurological": row[8],
            "skin": row[9],
        }
        for row in results
    ]
    logger.debug(f"Found {len(exams)} physical examination entries for hadm_id={hadm_id}")
    return exams


def get_lab_tests(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get the first entry of each lab test for a given admission.
    Uses window function to find earliest test result for each unique itemid.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with lab test details (may be empty)
    """
    query = """
        WITH RankedLabEvents AS (
            SELECT
                le.itemid,
                le.charttime,
                le.value,
                le.valueuom AS unit,
                le.ref_range_lower,
                le.ref_range_upper,
                le.flag,
                di.label AS test_name,
                ROW_NUMBER() OVER(PARTITION BY le.itemid ORDER BY le.charttime ASC) as rn
            FROM cdm_hosp.labevents le
            JOIN cdm_hosp.d_labitems di ON le.itemid = di.itemid
            WHERE le.hadm_id = %s
                AND le.value IS NOT NULL
        )
        SELECT
            test_name,
            value,
            unit,
            ref_range_lower,
            ref_range_upper,
            flag
        FROM RankedLabEvents
        WHERE rn = 1
        ORDER BY charttime
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    lab_tests = [
        {
            "test_name": row[0],
            "value": row[1],
            "unit": row[2],
            "ref_range_lower": row[3],
            "ref_range_upper": row[4],
            "flag": row[5],
        }
        for row in results
    ]
    logger.debug(f"Found {len(lab_tests)} unique lab tests for hadm_id={hadm_id}")
    return lab_tests


def get_radiology_reports(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get radiology report findings for a given admission.
    Only includes the 'findings' section from radiology reports.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with radiology report details (may be empty)
    """
    query = """
        SELECT
            charttime,
            note_type AS modality,
            text AS findings
        FROM
            cdm_note.radiology
        WHERE
            hadm_id = %s
            AND text IS NOT NULL
        ORDER BY
            charttime;
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    reports = [
        {
            "charttime": row[0],
            "modality": row[1],
            "findings": extract_findings_from_report(row[2]),
        }
        for row in results
    ]
    logger.debug(f"Found {len(reports)} radiology reports for hadm_id={hadm_id}")
    return reports


def get_ground_truth_diagnosis(cursor: psycopg.Cursor, hadm_id: int) -> str | None:
    """
    Get the first primary discharge diagnosis for a given admission.
    This represents the ground truth diagnosis.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        Primary diagnosis string, or None if not found
    """
    query = """
        SELECT title AS primary_diagnosis
        FROM cdm_note_extract.discharge_diagnosis
        WHERE hadm_id = %s
            AND is_primary = true
        ORDER BY seq_num
        LIMIT 1
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    logger.debug(f"No ground truth diagnosis found for hadm_id={hadm_id}")
    return None


def get_ground_truth_treatments_coded(cursor: psycopg.Cursor, hadm_id: int) -> list[str]:
    """
    Get coded procedures (ICD) for a given admission.
    This represents part of the ground truth treatments.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of coded procedure descriptions (may be empty)
    """
    query = """
        SELECT dicd.long_title
        FROM cdm_hosp.procedures_icd picd
        JOIN cdm_hosp.d_icd_procedures dicd
            ON picd.icd_code = dicd.icd_code
            AND picd.icd_version = dicd.icd_version
        WHERE picd.hadm_id = %s
        ORDER BY picd.seq_num
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    procedures = [row[0] for row in results if row[0]]
    logger.debug(f"Found {len(procedures)} coded procedures for hadm_id={hadm_id}")
    return procedures


def get_ground_truth_treatments_freetext(cursor: psycopg.Cursor, hadm_id: int) -> list[str]:
    """
    Get free-text procedures from notes for a given admission.
    This represents part of the ground truth treatments.
    Excludes procedures from patient's past history.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of free-text procedure descriptions (may be empty)
    """
    query = """
        SELECT title
        FROM cdm_note_extract.procedures
        WHERE hadm_id = %s
            AND (is_previous = false OR is_previous IS NULL)
        ORDER BY seq_num
    """
    cursor.execute(query, (hadm_id,))
    results = cursor.fetchall()

    procedures = [row[0] for row in results if row[0]]
    logger.debug(f"Found {len(procedures)} free-text procedures for hadm_id={hadm_id}")
    return procedures
