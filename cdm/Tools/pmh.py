from langchain.tools import tool
from typing import Dict, Any


def create_pmh_tool(case: Dict[str, Any]):
    @tool
    def request_past_medical_history(test_name: str) -> str:
        """Return the patient's past medical history."""
        pmh = case.get("past_medical_history")
        if not pmh:
            return "No past medical history available for this patient."

        result = ""
        for entry in pmh:
            note = entry.get("note", "N/A")
            category = entry.get("category", "N/A")
            result += f"- Category: {category}\n  Note: {note}\n"

        return result

    return request_past_medical_history
