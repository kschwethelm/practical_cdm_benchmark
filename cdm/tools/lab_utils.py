"""Lab test parsing utilities."""

import json
import re
from pathlib import Path

import pandas as pd
from loguru import logger
from thefuzz import fuzz, process

from cdm.tools.lab_mappings import (
    ADDITIONAL_LAB_TEST_MAPPING,
    ADDITIONAL_LAB_TEST_MAPPING_SYNONYMS,
    LAB_TEST_MAPPING_ALTERATIONS,
    LAB_TEST_MAPPING_SYNONYMS,
)

LAB_TEST_MAPPING_PATH = Path("/srv/student/cdm_v1/lab_test_mapping.json")


def load_lab_test_mapping() -> pd.DataFrame:
    """Load lab test mapping from JSON file."""
    if not LAB_TEST_MAPPING_PATH.exists():
        logger.warning(f"Lab test mapping not found at {LAB_TEST_MAPPING_PATH}")
        return pd.DataFrame()

    with open(LAB_TEST_MAPPING_PATH) as f:
        data = json.load(f)

    return pd.DataFrame(data)


def extract_short_and_long_name(test_name: str) -> tuple[str, str]:
    """Extract short name (abbreviation) and long name from test string.

    Example: 'Complete Blood Count (CBC)' -> ('CBC', 'Complete Blood Count')
    """
    match = re.search(r"(.*?)\s*\((.*?)\)", test_name)
    if match:
        long_name = match.group(1).strip()
        short_name = match.group(2).strip()
        return short_name, long_name
    else:
        return test_name.strip(), test_name.strip()


def remove_stop_words(sentence: str) -> str:
    """Remove stop words but keep uppercase single letters (lab abbreviations)."""
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "been",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "can",
        "order",
        "run",
        "level",
        "levels",
        "repeat",
        "check",
        "please",
    }

    # Keep uppercase single letters
    lowercase_single_letters = {w for w in stop_words if len(w) == 1}
    stop_words = stop_words - lowercase_single_letters

    words = sentence.split()
    filtered = [w for w in words if w.lower() not in stop_words or (len(w) == 1 and w.isupper())]

    # Remove 'A' if first word
    result = " ".join(filtered)
    result = re.sub(r"\bA\s", "", result)

    return result


def parse_lab_tests_action_input(action_input: str) -> list[str]:
    """Parse action input into list of lab tests.

    Args:
        action_input: Raw input string with lab tests

    Returns:
        List of individual test names
    """
    # Remove extra words
    for word in ["order", "run", "level[s]?", "repeat", "check"]:
        action_input = re.sub(rf"\b{word}\b", "", action_input, flags=re.IGNORECASE)

    # Replace 'and' with comma
    action_input = re.sub(r"\band\b", ",", action_input)

    # Replace newlines with comma
    action_input = re.sub(r"\n", ",", action_input)

    # Remove stop words
    action_input = remove_stop_words(action_input)

    # Split on comma (except when between parentheses)
    tests = re.split(r",\s*(?![^()]*\))", action_input)

    # Remove leading/trailing whitespace and empty entries
    tests = [t.strip() for t in tests if t and not t.isspace()]

    return tests


def convert_labs_to_itemid(tests: list[str], lab_test_mapping_df: pd.DataFrame) -> list[int | str]:
    """Convert list of test names to canonical itemids.

    Args:
        tests: List of test names
        lab_test_mapping_df: DataFrame with lab test mapping

    Returns:
        List of itemids (or test name strings if no match)
    """
    if lab_test_mapping_df.empty:
        logger.warning("Lab test mapping DataFrame is empty")
        return tests

    labels = lab_test_mapping_df["label"].tolist() if not lab_test_mapping_df.empty else []
    all_tests = []

    for test_full in tests:
        # Check ADDITIONAL mappings with fuzzy matching for panels
        panel_names = list(ADDITIONAL_LAB_TEST_MAPPING.keys())
        best_panel, panel_score = process.extractOne(test_full, panel_names, scorer=fuzz.ratio)

        if panel_score >= 85:  # match score threshold
            all_tests.extend(ADDITIONAL_LAB_TEST_MAPPING[best_panel])
            logger.debug(f"Matched '{test_full}' to panel '{best_panel}' (score: {panel_score})")
            continue

        # Check synonyms
        if test_full in ADDITIONAL_LAB_TEST_MAPPING_SYNONYMS:
            canonical_name = ADDITIONAL_LAB_TEST_MAPPING_SYNONYMS[test_full]
            if canonical_name in ADDITIONAL_LAB_TEST_MAPPING:
                all_tests.extend(ADDITIONAL_LAB_TEST_MAPPING[canonical_name])
                continue

        # Check alterations
        if test_full in LAB_TEST_MAPPING_ALTERATIONS:
            test_full = LAB_TEST_MAPPING_ALTERATIONS[test_full]

        # Extract short/long names
        test_short, test_long = extract_short_and_long_name(test_full)

        # Fuzzy matching against lab_test_mapping_df labels
        if labels:
            test_match, score = process.extractOne(test_full, labels, scorer=fuzz.ratio)

            if score < 90:
                # Try long name
                test_match, score = process.extractOne(test_long, labels, scorer=fuzz.ratio)

                if score < 90:
                    # Try short name (need exact match for abbreviations)
                    test_match, score = process.extractOne(test_short, labels, scorer=fuzz.ratio)

                    if score < 100:
                        test_match = ""
                        logger.debug(f"No canonical match for: {test_full}")

            # Get corresponding itemids
            if test_match:
                expanded_tests = lab_test_mapping_df.loc[
                    lab_test_mapping_df["label"] == test_match, "corresponding_ids"
                ].iloc[0]

                all_tests.extend(expanded_tests)
            else:
                # No match - keep original
                all_tests.append(test_full)
        else:
            # No labels available - keep original
            all_tests.append(test_full)

    # Apply synonym mapping
    all_tests = [LAB_TEST_MAPPING_SYNONYMS.get(t, t) for t in all_tests]

    # Remove duplicates while preserving order
    seen = set()
    unique_tests = []
    for test in all_tests:
        if test not in seen:
            seen.add(test)
            unique_tests.append(test)

    return unique_tests
