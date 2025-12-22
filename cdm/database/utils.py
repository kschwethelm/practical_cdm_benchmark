import re
from pathlib import Path

import yaml

# Load text processing configuration from library data directory
_CONFIG_PATH = Path(__file__).parent / "config_data" / "text_processing.yaml"


def _load_config() -> dict:
    """Load text processing configuration from YAML file."""
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_config = _load_config()

# Keywords loaded from configuration
DIAGNOSIS_SCRUB_KEYWORDS = _config["diagnosis_scrub_keywords"]
MODALITY_KEYWORDS = _config["modality_keywords"]
REGION_KEYWORDS = _config["region_keywords"]
BAD_RAD_FIELDS = _config["bad_rad_fields"]


def get_pathology_type_from_string(ground_truth_diagnosis: str) -> str | None:
    """
    Finds the matching 'pathology_type' (e.g., 'diverticulitis')
    from a specific ground_truth string (e.g., 'Complicated diverticulitis...').
    If multiple diagnoses are separated by commas, checks each part.
    """
    if not ground_truth_diagnosis:
        return None

    # Split by comma and check each part
    diagnosis_parts = [part.strip() for part in ground_truth_diagnosis.split(",")]

    for diagnosis_part in diagnosis_parts:
        search_string = diagnosis_part.lower()

        # Iterate through our keyword dictionary
        for category, keywords in DIAGNOSIS_SCRUB_KEYWORDS.items():
            # Check if any keyword for this category is in the ground truth string
            for keyword in keywords:
                # Use regex word boundaries to match whole words
                if re.search(r"\b" + re.escape(keyword.lower()) + r"\b", search_string):
                    return category

    # If no match is found (e.g., for a new negative control case)
    return None


def scrub_physical_exam_text(text: str) -> str:
    """
    Removes discharge exams and additional physical exams from physical examination text.
    Should be called before scrub_text() for physical exam data.

    Args:
        text: The physical exam text to scrub

    Returns:
        Cleaned physical exam text with discharge exams and duplicates removed
    """
    if not text:
        return ""

    # Manually checked the physical exams with the comparison script so that the following patterns don't remove too much text

    # Remove text after discharge-related phrases, but avoid discharge in normal sentences
    # For "on/upon/at/in discharge" or "on/upon/at/in day of discharge" or "day of discharge" (optionally preceded by exam-related headers)
    # Handles common misspellings: Physical, Phsyical, Physcial
    text = re.sub(
        r"(?:\b(?:(?:Physical|Phsyical|Physcial)\s+Exam(?:ination)?|Exam(?:ination)?|PE|Patient\s+examined)\s+)?\b(?:(?:on|upon|at|in)\s+(?:(day|time)\s+of\s+)?|day\s+of\s+)discharge\b.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    # Handle "discharge vs" case
    text = re.sub(r"\bdischarge\s+vs\b.*", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # Handle "discharge physical" case, also catch typos like "phsycial"
    text = re.sub(
        r"\bdischarge\s+ph[sy]+[sy]?[iyc]+a?l\b.*", "", text, flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # Handle specific discharge-related "Physical:" patterns (including literal "___")
    # Also removes "ACS Discharge Physical Exam ___:"
    text = re.sub(
        r"(?:\b(?:ACS\s+)?(?:Discharge|Transfer|D/C)\s+(?:Physical\s+Exam\s+)?|___\s*)Physical\s*:.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    # Handle "at [prefix]ischarge Exam" pattern (corrupted discharge text)
    text = re.sub(
        r"\bat\s+.{0,3}ischarge\s+exam\b.*", "", text, flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # Handle "Discharge" as a standalone section header (at start of line)
    text = re.sub(r"(?:^|\n)\s*Discharge\b.*", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # Handle "--DISCHARGE--" pattern
    text = re.sub(r"--DISCHARGE--.*", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # Handle standalone all-caps "DISCHARGE"
    text = re.sub(r"\bDISCHARGE\b.*", "", text, flags=re.DOTALL).strip()

    # Then handle "discharge" with colon, colon optional for "discharge exam"/"discharge pe"
    # Also removes "Prior Discharge:" and "On D/C:"
    discharge_pattern = re.compile(
        r"\b(?:Prior\s+discharge\s*:|discharge\s*:|discharge\s+exam|discharge\s+pe|discharge\s+labs|on\s+discharged\s*:|On\s+D/C\s*:|Time\s+of\s+Discharge\s*:|D/C\s*:|DISPO).*",
        re.IGNORECASE | re.DOTALL,
    )
    text = discharge_pattern.sub("", text).strip()

    # Remove labs, imaging, and diagnostics sections (but keep ADMISSION LABS)
    text = re.sub(
        r"(?<!ADMISSION\s)\b(?:Labs and imaging|Labs|Laboratory|Imaging|Diagnostics)\s*:.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    # Pattern matches major section headers for additional physical exam sections:
    # Excludes "Scrotal exam:" and "Pelvic exam:" from being matched
    physical_exam_pattern = re.compile(
        r"(?:^|\n.{0,15})(?:PHYSICAL\s+EXAM:?|TRANSFER\s+EXAM:|EXAMINATION:|(?<!Scrotal\s)(?<!Pelvic\s)EXAM:|P/E:|PE:|VS:|Vital\s+signs:|AMA:)",
        re.IGNORECASE,
    )
    matches = list(physical_exam_pattern.finditer(text))

    # Find any additional physical exam section that appears after the first ~200 characters and remove
    # Trial and error with the comparison script resulted in 200 character cutoff
    # If "Gen:" appears shortly after the header, keep it (it's likely a continuation)
    for match in matches:
        if match.start() > 200:
            # Check if "Gen:" or "HEENT:" appears within 22 (cutoff to avoid false positives but get all false negatives) characters after this header
            # Very specific to catch only the few false positives following this pattern
            remaining_text = text[match.start() :]
            if not re.search(r"\b(?:Gen|HEENT)\s*:", remaining_text[:22], re.IGNORECASE):
                text = text[: match.start()].strip()
                break

    # Special case for one case with only AMA exam
    text = text.replace("Prior to leaving AMA...", "").strip()

    # False negatives that miss the above patterns
    # Remove duplicate HEENT sections (keep only first occurrence)
    heent_pattern = re.compile(r"\bHEENT\s*:", re.IGNORECASE)
    heent_matches = list(heent_pattern.finditer(text))
    if len(heent_matches) > 1:
        # Remove everything from the second HEENT onwards
        text = text[: heent_matches[1].start()].strip()

    # Remove duplicate exam starting with vital signs pattern
    # This catches exams that don't have a header but start with temperature later in the text
    duplicate_vitals_pattern = re.compile(r"\s+T\d+\.?\d*\s+HR\s+\d+\s+BP\s+\d+/\d+", re.IGNORECASE)
    vitals_match = duplicate_vitals_pattern.search(text)
    if vitals_match and vitals_match.start() > 200:
        text = text[: vitals_match.start()].strip()

    # Remove lab values that appear without header
    # Pattern matches common lab value format: WBC followed by number
    lab_values_pattern = re.compile(r"\s+WBC\s+\d+\.?\d*,?\s+", re.IGNORECASE)
    lab_match = lab_values_pattern.search(text)
    if lab_match:
        text = text[: lab_match.start()].strip()

    # Remove section headers that may appear in the text
    text = re.sub(
        r"\b(?:PE|Physical\s+Exam|Physical\s+Examination)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Remove specific string about 10 system review
    text = text.replace("10 system review negative, except as stated above in HPI.", "").strip()

    # Replace sequences of more than 4 "x" characters with "___"
    text = re.sub(r"x{5,}", "___", text, flags=re.IGNORECASE).strip()

    # Remove multiple "=", "_" symbols (more than 1) at the beginning and end of text
    text = re.sub(r"^=={2,}", "", text).strip()
    text = re.sub(r"=={2,}$", "", text).strip()
    text = re.sub(r"^__{4,}", "", text).strip()
    text = re.sub(r"__{4,}$", "", text).strip()

    # Remove "___:" pattern from beginning and end
    text = re.sub(r"^___:", "", text).strip()
    text = re.sub(r"___:$", "", text).strip()

    return text


def scrub_text(text: str, pathology_type: str | None) -> str:
    """
    Removes mentions of the diagnosis and related procedures from
    a block of text, replacing them with '___' as per CDMv1.

    For physical exam text, call scrub_physical_exam_text() first.

    Args:
        text: The text to scrub
        pathology_type: The type of pathology (e.g., 'pancreatitis')
    """
    if not text:
        return ""

    # Replace newlines with spaces
    text = text.replace("\n", " ")

    if not pathology_type:
        return text  # No scrubbing needed if no pathology type

    keywords_to_scrub = DIAGNOSIS_SCRUB_KEYWORDS.get(pathology_type, [])

    if not keywords_to_scrub:
        return text

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in keywords_to_scrub) + r")\b", re.IGNORECASE
    )

    text = pattern.sub("___", text)

    return text


def parse_report(report: str) -> dict:
    """
    Splits the report into a dictionary of {SECTION_HEADER: Content}.
    Replicates logic from CDMv1 repo.
    """
    if not report:
        return {}
    lines = report.strip().split("\n")
    report_dict = {}

    # Check if the first line ends with a colon
    if lines and lines[0].strip() and lines[0].isupper() and not lines[0].strip().endswith(":"):
        lines[0] = lines[0].strip() + ":"

    # Check for other header lines (ALL CAPS)
    for i, line in enumerate(lines):
        if line.isupper() and ":" not in line:
            lines[i] = line.strip() + ":"

    report = "\n".join(lines)
    pattern = r"(?m)^([A-Z \t,._-]+):((?:(?!^[A-Z \t,._-]+:).)*)"
    sections = re.findall(pattern, report, re.DOTALL)

    for section in sections:
        report_dict[section[0].strip()] = section[1].strip()

    return report_dict


def extract_findings_from_report(raw_report_text: str) -> str:
    """
    Extracts relevant sections for reasoning.
    """
    if not raw_report_text:
        return ""

    sections = parse_report(raw_report_text)

    text_clean = ""

    for field, content in sections.items():
        # Check if field starts with any bad field string
        is_bad = any(field.startswith(bad) for bad in BAD_RAD_FIELDS)

        if not is_bad and content.strip():
            text_clean += f"{field}:\n{content}\n\n"

    return text_clean.strip()


def derive_modality(exam_name: str, text: str) -> str:
    """
    Uses modality keywords to derive test modality mentioned in exam_name and text
    """
    if not exam_name:
        return "Unknown"
    exam_upper = exam_name.upper()

    # Derive Modality from exam_name
    modality = "Unknown"
    for mod, keywords in MODALITY_KEYWORDS.items():
        pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"
        if re.search(pattern, exam_upper):
            modality = mod
            break
    if modality == "Unknown" and exam_upper.startswith("CHEST"):
        modality = "Radiograph"

    # Further check text if modality is still unknown
    if modality == "Unknown" and text:
        text_upper = text.upper()
        for mod, keywords in MODALITY_KEYWORDS.items():
            pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"
            if re.search(pattern, text_upper):
                modality = mod
                break

    return modality


def derive_region(exam_name: str, text: str) -> str:
    """
    Uses region keywords to derive test region mentioned in exam_name and text
    """
    if not exam_name:
        return "Unknown"
    exam_upper = exam_name.upper()

    # Derive Region from exam_name
    region = "Unknown"
    for reg, keywords in REGION_KEYWORDS.items():
        pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"
        if re.search(pattern, exam_upper):
            region = reg
            break

    # Further check text if region is still unknown
    if region == "Unknown" and text:
        text_upper = text.upper()
        for reg, keywords in REGION_KEYWORDS.items():
            pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"
            if re.search(pattern, text_upper):
                region = reg
                break

    return region
