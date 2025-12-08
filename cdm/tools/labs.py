from langchain.tools import tool

from cdm.benchmark.data_models import DetailedLabResult, HadmCase, MicrobiologyEvent
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
    """Request laboratory test and/or microbiology results for the current patient.

    Supports:
    - Single tests: "CBC", "Creatinine", "Glucose"
    - Multiple tests: "CBC, BMP, lipase"
    - Panels: "Complete Blood Count", "Basic Metabolic Panel", "LFTs"
    - Microbiology: "Blood culture", "Urine culture", "Wound culture"
    - Variations: "order CBC and electrolytes", "run liver enzymes"

    Args:
        test_name: Lab/microbiology test name(s). Can be comma separated or use 'and'.

    Returns:
        Formatted lab results or error message
    """
    case: HadmCase = get_current_case()
    lab_results = case.lab_results
    microbiology_events = case.microbiology_events

    if not lab_results:
        return "No laboratory results available for this patient."

    # Parse input into list of test names (handles "CBC, BMP" or "CBC and electrolytes")
    test_names = parse_lab_tests_action_input(test_name)

    # Convert to itemids using fuzzy matching and panel expansion
    itemids = convert_labs_to_itemid(test_names, LAB_TEST_MAPPING_DF)

    # Collect matching results
    results = []
    not_found = []

    for item in itemids:
        if isinstance(item, int):
            # First check lab results
            matching_labs = [lab for lab in lab_results if lab.itemid == item]

            if matching_labs:
                for lab in matching_labs:
                    results.append(format_lab_result(lab))
            else:
                # Fallback: check microbiology (Hager's logic)
                matching_microbio = [
                    micro for micro in microbiology_events if micro.test_itemid == item
                ]

                if matching_microbio:
                    for micro in matching_microbio:
                        results.append(format_microbiology_result(micro))
                else:
                    not_found.append(item)
        else:
            # String search fallback (couldn't map to itemid)
            found = False

            # Try lab results first
            for lab in lab_results:
                if str(item).lower() in lab.test_name.lower():
                    results.append(format_lab_result(lab))
                    found = True

            # If not found in labs, try microbiology
            if not found:
                for micro in microbiology_events:
                    if micro.test_name and str(item).lower() in micro.test_name.lower():
                        results.append(format_microbiology_result(micro))
                        found = True

            if not found:
                not_found.append(str(item))

    # Build response
    if not results:
        return f"The requested lab tests are not available for this patient: {test_name}"
    response = "\n".join(results)
    if not_found:
        response += f"\n\nCould not find: {', '.join(str(x) for x in not_found)}"

    return response


def format_lab_result(lab: DetailedLabResult) -> str:
    """Format lab result as: (Fluid) Test Name: Value (ref: lower-upper)"""
    value = lab.value or "Unknown"

    # Fluid prefix (e.g., Blood, Urine)
    fluid = lab.fluid or "Unknown"

    # Reference range
    ref_str = ""
    if lab.ref_range_lower is not None or lab.ref_range_upper is not None:
        ref_str = f" (ref: {lab.ref_range_lower}-{lab.ref_range_upper})"

    return f"({fluid}) {lab.test_name}: {value}{ref_str}"


def format_microbiology_result(micro: MicrobiologyEvent) -> str:
    """Format microbiology result as: (Microbiology) Test Name: Value

    Matches Hager's format where fluid is set to "Microbiology" for micro tests.
    """
    test_name = micro.test_name or "Unknown Test"

    # Value from organism or comments
    if micro.organism_name:
        value = micro.organism_name
    elif micro.comments:
        value = micro.comments
    else:
        value = "No growth"

    return f"(Microbiology) {test_name}: {value}"
