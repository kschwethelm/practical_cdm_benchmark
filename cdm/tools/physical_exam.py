from langchain.tools import tool

from cdm.tools.context import get_current_case


@tool
def physical_examination() -> str:
    """Perform physical examination of patient and receive the observations."""
    case = get_current_case()
    pe = case.get("physical_exam_text", "No physical exam data available.")
    return pe
