import psycopg
from loguru import logger


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
