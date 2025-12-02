from langchain.tools import tool

from cdm.benchmark.data_models import DetailedLabResult, HadmCase
from cdm.tools.context import get_current_case
from cdm.tools.lab_utils import (
    convert_labs_to_itemid,
    load_lab_test_mapping,
    parse_lab_tests_action_input,
)

# Load mapping once
LAB_TEST_MAPPING_DF = load_lab_test_mapping()


@tool
def request_lab_test(test_name: str) -> str:
    """Request laboratory test results for the current patient.

    Supports:
    - Single tests: "CBC", "Creatinine", "Glucose"
    - Multiple tests: "CBC, BMP, lipase"
    - Panels: "Complete Blood Count", "Basic Metabolic Panel", "LFTs"
    - Variations: "order CBC and electrolytes", "run liver enzymes"

    Args:
        test_name: Lab test name(s). Can be comma separated or use 'and'.

    Returns:
        Formatted lab results or error message
    """
    case: HadmCase = get_current_case()
    lab_results = case.lab_results

    if not lab_results:
        return "No laboratory results available for this patient."

    # Parse input into list of test names (handles "CBC, BMP" or "CBC and electrolytes")
    test_names = parse_lab_tests_action_input(test_name)

    # Convert to itemids using fuzzy matching and panel expansion
    itemids = convert_labs_to_itemid(test_names, LAB_TEST_MAPPING_DF)

    # Collect matching results
    results = []
    not_found_itemids = []
    not_found_strings = []

    for item in itemids:
        if isinstance(item, int):
            # It's an itemid, find in patient's lab results
            matching_labs = [lab for lab in lab_results if lab.itemid == item]

            if matching_labs:
                for lab in matching_labs:
                    results.append(format_lab_result(lab))
            else:
                # Itemid exists in mapping but not available for this patient
                not_found_itemids.append(item)
        else:
            # It's a string (couldn't map to itemid), try substring search
            found = False
            for lab in lab_results:
                if str(item).lower() in lab.test_name.lower():
                    results.append(format_lab_result(lab))
                    found = True

            if not found:
                not_found_strings.append(item)

    # Build response
    if not results and not not_found_strings:
        return f"The requested lab tests are not available for this patient: {test_name}"

    response = "\n".join(results) if results else ""

    if not_found_strings:
        if response:
            response += "\n\n"
        response += f"Could not find: {', '.join(not_found_strings)}"

    return response if response else f"No laboratory results found for: {test_name}"


def format_lab_result(lab: DetailedLabResult) -> str:
    """Format a single lab result with category, fluid, value, and reference range."""
    value = lab.value or "Unknown"
    ref_range_lower = lab.ref_range_lower
    ref_range_upper = lab.ref_range_upper

    # Format reference range
    ref_str = ""
    if ref_range_lower is not None or ref_range_upper is not None:
        ref_str = f" (ref: {ref_range_lower}-{ref_range_upper})"

    # Format category and fluid
    category = lab.category or ""
    fluid = lab.fluid or ""
    category_str = ""
    if category or fluid:
        parts = [p for p in (category, fluid) if p]
        category_str = f" [{' | '.join(parts)}]"

    return f"- {lab.test_name}{category_str}: {value}{ref_str}"
