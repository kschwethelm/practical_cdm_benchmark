import re

# Define the keywords to scrub from all text
# Currently limited to 4 acute abdominal conditions from CDMv1 paper
DIAGNOSIS_SCRUB_KEYWORDS = {
    "appendicitis": ["acute appendicitis", "appendicitis", "appendectomy", "tip appendicitis"],
    "cholecystitis": ["acute cholecystitis", "cholecystitis", "cholecystostomy"],
    "pancreatitis": [
        "acute pancreatitis",
        "pancreatitis",
        "pancreatectomy",
        "autoimmune pancreatitis",
        "uncomplicated pancreatitis",
    ],
    "diverticulitis": [
        "acute diverticulitis",
        "diverticulitis",
        "perforated diverticulitis",
        "complicated diverticulitis",
    ],
}

# Adapted from CDMv1, might need to be expanded with more keywords for complete dataset
MODALITY_KEYWORDS = {
    "CT": ["CT", "CTA", "COMPUTED TOMOGRAPHY"],
    "MR": ["MR", "MRI", "MRA", "MAGNETIC RESONANCE"],
    "US": ["US", "ULTRASOUND", "SONOGRAM", "DUPLEX"],
    "XR": ["XR", "X-RAY", "RADIOGRAPH", "CHEST (", "ABDOMEN (", "PELVIS ("],
    "NM": ["NM", "NUCLEAR", "SCINTIGRAPHY"],
    "FL": ["FLUORO", "SWALLOW", "ENEMA"],
    "ERCP": ["ERCP"],
}

REGION_KEYWORDS = {
    "Abdomen": ["ABDOMEN", "ABD", "LIVER", "GALLBLADDER", "PANCREAS", "SPLEEN", "RENAL", "KIDNEY"],
    "Chest": ["CHEST", "THORAX", "LUNG"],
    "Pelvis": ["PELVIS", "PELVIC"],
    "Head": ["HEAD", "BRAIN", "CRANIUM", "SINUS"],
    "Neck": ["NECK", "CERVICAL"],
    "Spine": ["SPINE", "LUMBAR", "THORACIC"],
    "Extremity": ["KNEE", "SHOULDER", "HIP", "ARM", "LEG", "FOOT", "HAND"],
}


def get_pathology_type_from_string(ground_truth_diagnosis: str) -> str | None:
    """
    Finds the matching 'pathology_type' (e.g., 'diverticulitis')
    from a specific ground_truth string (e.g., 'Complicated diverticulitis...').
    """
    if not ground_truth_diagnosis:
        return None

    search_string = ground_truth_diagnosis.lower()

    # Iterate through our keyword dictionary
    for category, keywords in DIAGNOSIS_SCRUB_KEYWORDS.items():
        # Check if any keyword for this category is in the ground truth string
        for keyword in keywords:
            # Use regex word boundaries to match whole words
            if re.search(r"\b" + re.escape(keyword.lower()) + r"\b", search_string):
                return category  # Found it!

    # If no match is found (e.g., for a new negative control case)
    return None


def scrub_text(text: str, pathology_type: str | None) -> str:
    """
    Removes mentions of the diagnosis and related procedures from
    a block of text, replacing them with '___' as per CDMv1.
    """
    if not text:
        return ""
    if not pathology_type:
        return text  # No scrubbing needed if no pathology type

    keywords_to_scrub = DIAGNOSIS_SCRUB_KEYWORDS.get(pathology_type, [])

    if not keywords_to_scrub:
        return text

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in keywords_to_scrub) + r")\b", re.IGNORECASE
    )

    return pattern.sub("___", text)


def parse_report(report):
    """
    Splits the report into a dictionary of {SECTION_HEADER: Content}.
    Replicates logic from CDMv1 repo.
    """
    if not report:
        return {}
    lines = report.strip().split("\n")
    report_dict = {}

    # Check if the first line ends with a colon
    if lines and lines[0].isupper() and lines[0].strip()[-1] != ":":
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
    Prioritizes 'FINDINGS' section, falls back to removing 'bad' sections.
    """
    if not raw_report_text:
        return ""

    BAD_RAD_FIELDS = [
        "CLINICAL HISTORY",
        "MEDICAL HISTORY",
        "CLINICAL INFORMATION",
        "COMPARISON",
        "COMPARISONS",
        "COMMENT",
        "CONCLUSION",
        "HISTORY",
        "IMPRESSION",
        "CLINICAL INDICATION",
        "INDICATION",
        "OPERATORS",
        "REASON",
        "REFERENCE",
        "DATE",
    ]

    sections = parse_report(raw_report_text)

    # Explicitly look for "FINDINGS"
    for header, content in sections.items():
        if "FINDINGS" in header and "SUMMARY" not in header:
            # e.g. "FINDINGS", "CT ABDOMEN FINDINGS"
            return content.strip()

    # Fallback to Negative Filtering (CDMv1 Logic)
    # If no explicit findings section, we construct text from all non-bad sections.
    text_clean = ""

    for field, content in sections.items():
        # Check if field starts with any bad field string
        is_bad = any(field.startswith(bad) for bad in BAD_RAD_FIELDS)

        if not is_bad and content.strip():
            text_clean += f"{field}:\n{content}\n\n"

    return text_clean.strip()


def derive_modality(exam_name: str, text: str) -> str:
    if not exam_name:
        return "Unknown", "Unknown"
    exam_upper = exam_name.upper()

    # Derive Modality from exam_name
    modality = "Unknown"
    for mod, keywords in MODALITY_KEYWORDS.items():
        if any(kw in exam_upper for kw in keywords):
            modality = mod
            break
    if modality == "Unknown" and exam_upper.startswith("CHEST"):
        modality = "XR"

    # Further check text if modality is still unknown
    if modality == "Unknown" and text:
        text_upper = text.upper()
        for mod, keywords in MODALITY_KEYWORDS.items():
            if any(kw in text_upper for kw in keywords):
                modality = mod
                break

    return modality


def derive_region(exam_name: str, text: str) -> str:
    if not exam_name:
        return "Unknown"
    exam_upper = exam_name.upper()

    # Derive Region from exam_name
    region = "Unknown"
    for reg, keywords in REGION_KEYWORDS.items():
        if any(kw in exam_upper for kw in keywords):
            region = reg
            break

    # Further check text if region is still unknown
    if region == "Unknown" and text:
        text_upper = text.upper()
        for reg, keywords in REGION_KEYWORDS.items():
            if any(kw in text_upper for kw in keywords):
                region = reg
                break

    return region
