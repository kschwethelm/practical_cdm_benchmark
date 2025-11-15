from langchain.tools import tool

CURRENT_CASE = None  # To be set when loading a case


@tool
def request_lab_test(test_name: str) -> str:
    """Return lab results based on the patient case."""
    if CURRENT_CASE is None:
        return "Error: no case loaded."

    lab = CURRENT_CASE.get("first_lab_result")
    if not lab:
        return "No lab results available for this patient."

    result = (
        #f"Lab result:\n"
        f"- Time: {lab.get('charttime')}\n"
        f"- Test ID: {lab.get('itemid', 'N/A')}\n"
        f"- Value: {lab.get('value', 'N/A')}\n"
        f"- Text Value: {lab.get('valueuom', 'N/A')}\n"
        f"- Numeric Value: {lab.get('valuenum', 'N/A')}\n"
    )

    return result
