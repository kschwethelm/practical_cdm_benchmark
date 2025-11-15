from langchain.tools import tool

CURRENT_CASE = None # To be set when loading a case


@tool
def request_microbio_test(test_name: str) -> str:
    """Return microbiology results for the patient (blood/urine cultures, etc.)."""
    if CURRENT_CASE is None:
        return "Error: no case loaded."

    bio = CURRENT_CASE.get("first_microbiology_result")
    if not bio:
        return "No microbiology results available for this patient."

    result = (
        #f"Microbiology result:\n"
        f"- Time collected: {bio.get('charttime', 'N/A')}\n"
        f"- Specimen type: {bio.get('spec_type_desc', 'N/A')}\n"
        f"- Test name: {bio.get('test_name', 'N/A')}\n"
        f"- Organism found: {bio.get('org_name', 'N/A')}\n"
        f"- Interpretation: {bio.get('interpretation', 'N/A')}\n"
    )

    return result
