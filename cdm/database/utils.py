import re
from typing import List, Optional

# Define the keywords to scrub from all text
# (This is from the `extract_info` call in the old notebook)
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


def get_pathology_type_from_string(ground_truth_diagnosis: str) -> Optional[str]:
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


def scrub_text(text: str, pathology_type: str) -> str:
    """
    Removes mentions of the diagnosis and related procedures from
    a block of text, replacing them with '___' as per CDMv1.
    """
    if not text or not pathology_type:
        return ""

    keywords_to_scrub = DIAGNOSIS_SCRUB_KEYWORDS.get(pathology_type, [])

    if not keywords_to_scrub:
        return text

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in keywords_to_scrub) + r")\b", re.IGNORECASE
    )

    scrubbed_text = pattern.sub("___", text)
    return scrubbed_text


def extract_findings_from_report(raw_report_text: str) -> str:
    """
    Extracts only the 'findings' section from a raw radiology report
    and discards the rest

    This is the core method from the CDMv1 paper (page 11).
    """
    if not raw_report_text:
        return ""

    # Use re.DOTALL so '.' matches newline characters
    # Use re.IGNORECASE to match "FINDINGS:", "Findings:", etc.
    # This regex captures all text between "FINDINGS:" and "IMPRESSION:"
    match = re.search(
        r"FINDINGS?:(.*?)(IMPRESSION:|CONCLUSIONS?:|RECOMMENDATION:|NOTIFICATION:|SUMMARY:)",
        raw_report_text,
        re.DOTALL | re.IGNORECASE,
    )

    findings_text = ""
    if match:
        # We found both markers, get the text in between
        findings_text = match.group(1).strip()
    else:
        # If "IMPRESSION:" isn't found, try to just get the "FINDINGS:"
        # section and hope for the best.
        match_findings_only = re.search(
            r"FINDINGS?:(.*?)(?:\n\s*\n[A-Z_ ]+:|\Z)", raw_report_text, re.DOTALL | re.IGNORECASE
        )
        if match_findings_only:
            findings_text = match_findings_only.group(1).strip()
        else:
            # Could not find a "FINDINGS:" section, return empty
            return ""

    return findings_text
