import psycopg
from loguru import logger

from cdm.database.utils import derive_modality, derive_region, extract_findings_from_report


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
        SELECT history_of_present_illness, past_medical_history
        FROM cdm_note_extract.discharge_free_text
        WHERE hadm_id = %s
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return result[0] + "\n\nPast Medical History: " + result[1]
    logger.debug(f"No history of present illness found for hadm_id={hadm_id}")
    return None


def get_physical_examination(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get physical examination findings for a given admission.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        Physical examination string, or None if not found
    """
    query = """
        SELECT physical_examination
        FROM cdm_note_extract.discharge_free_text
        WHERE hadm_id = %s
    """
    cursor.execute(query, (hadm_id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    logger.debug(f"No physical exam text found for hadm_id={hadm_id}")
    return None


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
        WITH CombinedLabEvents AS (
            SELECT itemid, charttime, valuenum, value, valueuom, flag, comments,
                   ref_range_lower, ref_range_upper, hadm_id, storetime
            FROM cdm_hosp.labevents
            WHERE hadm_id = %s

            UNION ALL

            SELECT itemid, charttime, valuenum, value, valueuom, flag, comments,
                   ref_range_lower, ref_range_upper, hadm_id, storetime
            FROM cdm_hosp.labevents_assigned
            WHERE hadm_id = %s
        ),
        FilteredLabEvents AS (
            SELECT
                le.itemid,
                le.charttime,
                le.storetime,
                CASE
                    WHEN le.valuenum IS NOT NULL AND CAST(le.valuenum AS TEXT) != '___' THEN
                        CASE
                            WHEN le.valueuom IS NOT NULL THEN CAST(le.valuenum AS TEXT) || ' ' || le.valueuom
                            ELSE CAST(le.valuenum AS TEXT)
                        END
                    WHEN le.value IS NOT NULL AND le.value != '___' THEN
                        CASE
                            WHEN le.valueuom IS NOT NULL THEN le.value || ' ' || le.valueuom
                            ELSE le.value
                        END
                    WHEN le.flag IS NOT NULL THEN le.flag
                    WHEN le.comments IS NOT NULL THEN le.comments
                    ELSE NULL
                END AS valuestr,
                le.ref_range_lower,
                le.ref_range_upper,
                di.label AS test_name,
                di.fluid,
                di.category
            FROM CombinedLabEvents le
            JOIN cdm_hosp.d_labitems di ON le.itemid = di.itemid
        ),
        RankedLabEvents AS (
            SELECT
                itemid,
                charttime,
                valuestr,
                ref_range_lower,
                ref_range_upper,
                test_name,
                fluid,
                category,
                ROW_NUMBER() OVER(PARTITION BY itemid ORDER BY charttime ASC, storetime ASC NULLS LAST) as rn
            FROM FilteredLabEvents
            WHERE valuestr IS NOT NULL
                AND valuestr != '___'
        )
        SELECT
            test_name,
            valuestr AS value,
            ref_range_lower,
            ref_range_upper,
            fluid,
            category,
            itemid
        FROM RankedLabEvents
        WHERE rn = 1
        ORDER BY charttime
    """

    cursor.execute(query, (hadm_id, hadm_id))
    results = cursor.fetchall()

    lab_tests = [
        {
            "test_name": row[0],
            "value": row[1],
            "ref_range_lower": row[2],
            "ref_range_upper": row[3],
            "fluid": row[4],
            "category": row[5],
            "itemid": row[6],
        }
        for row in results
    ]
    logger.debug(f"Found {len(lab_tests)} unique lab tests for hadm_id={hadm_id}")
    return lab_tests


def get_microbiology_events(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get microbiology tests for a given admission, merging multiple organisms/comments
    for the same test_itemid and charttime.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with microbiology event details (may be empty)
    """
    query = """
        WITH CombinedMicroEvents AS (
            SELECT test_name, spec_type_desc, org_name, comments, charttime, test_itemid, hadm_id, storetime
            FROM cdm_hosp.microbiologyevents
            WHERE hadm_id = %s

            UNION ALL

            SELECT test_name, spec_type_desc, org_name, comments, charttime, test_itemid, hadm_id, storetime
            FROM cdm_hosp.microbiologyevents_assigned
            WHERE hadm_id = %s
        ),
        FilteredMicroEvents AS (
            SELECT
                micro.test_name,
                micro.spec_type_desc,
                micro.org_name,
                micro.comments,
                micro.charttime,
                micro.storetime,
                micro.test_itemid
            FROM CombinedMicroEvents micro
            WHERE ((micro.org_name IS NOT NULL AND micro.org_name != 'CANCELLED') OR (micro.comments IS NOT NULL AND micro.comments != '___'))
        ),
        RankedMicroEvents AS (
            SELECT
                test_name,
                spec_type_desc,
                STRING_AGG(DISTINCT org_name, ', ' ORDER BY org_name) FILTER (WHERE org_name IS NOT NULL) AS org_name,
                STRING_AGG(DISTINCT comments, ', ' ORDER BY comments) FILTER (WHERE comments IS NOT NULL) AS comments,
                charttime,
                MIN(storetime) as storetime,
                test_itemid,
                ROW_NUMBER() OVER(PARTITION BY test_itemid ORDER BY charttime ASC, MIN(storetime) ASC NULLS LAST) as rn
            FROM FilteredMicroEvents
            GROUP BY test_name, spec_type_desc, charttime, test_itemid
        )
        SELECT
            test_name,
            spec_type_desc,
            org_name,
            comments,
            charttime,
            test_itemid
        FROM RankedMicroEvents
        WHERE rn = 1
            AND (org_name IS NOT NULL OR comments IS NOT NULL)
        ORDER BY charttime
    """

    cursor.execute(query, (hadm_id, hadm_id))
    results = cursor.fetchall()

    microbiology_events = [
        {
            "test_name": row[0],
            "spec_type_desc": row[1],
            "organism_name": row[2],
            "comments": row[3],
            "charttime": row[4],
            "test_itemid": row[5],
        }
        for row in results
    ]
    logger.debug(f"Found {len(microbiology_events)} microbiology events for hadm_id={hadm_id}")
    return microbiology_events


def get_radiology_reports(cursor: psycopg.Cursor, hadm_id: int) -> list[dict]:
    """
    Get the first entry of each radiology report for a given admission.
    Uses window function to find earliest report for each unique note_id.

    Args:
        cursor: Database cursor
        hadm_id: Hospital admission ID

    Returns:
        list of dicts with radiology report details (may be empty)
    """
    query = """
        WITH CombinedRadiology AS (
            SELECT note_id, hadm_id, text, charttime
            FROM cdm_note.radiology
            WHERE hadm_id = %s

            UNION ALL

            SELECT note_id, hadm_id, text, charttime
            FROM cdm_note.radiology_assigned
            WHERE hadm_id = %s
        ),
        FilteredRadiology AS (
            SELECT
                rad.charttime,
                det.field_value AS exam_name,
                rad.text AS findings,
                rad.note_id
            FROM CombinedRadiology rad
            JOIN cdm_note.radiology_detail det ON rad.note_id = det.note_id
            WHERE rad.text IS NOT NULL
                AND det.field_name = 'exam_name'
        ),
        RankedRadiology AS (
            SELECT
                charttime,
                exam_name,
                findings,
                note_id,
                ROW_NUMBER() OVER(PARTITION BY note_id ORDER BY charttime ASC) as rn
            FROM FilteredRadiology
        )
        SELECT
            exam_name,
            findings,
            note_id
        FROM RankedRadiology
        WHERE rn = 1
        ORDER BY charttime;
    """
    cursor.execute(query, (hadm_id, hadm_id))
    results = cursor.fetchall()

    reports = [
        {
            "exam_name": row[0],
            "modality": derive_modality(row[0], row[1]),
            "region": derive_region(row[0], row[1]),
            "findings": extract_findings_from_report(row[1]),
            "note_id": row[2],
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
           AND seq_num = 1
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
