from langchain.tools import tool

CURRENT_CASE = None  # To be set when loading a case


@tool
def request_past_medical_history(test_name: str) -> str:
    """Return the patient's past medical history."""
    
    if CURRENT_CASE is None:
        return "Error: no case loaded."

    pmh = CURRENT_CASE.get("past_medical_history")
    if not pmh:
        return "No past medical history available for this patient."

    result = ""
    for entry in pmh:
        note = entry.get("note", "N/A")
        category = entry.get("category", "N/A")
        result += f"- Category: {category}\n  Note: {note}\n"

    return result