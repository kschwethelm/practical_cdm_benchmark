from langchain.tools import tool

from cdm.benchmark.data_models import HadmCase
from cdm.tools.context import get_current_case


@tool
def physical_examination() -> str:
    """Perform physical examination of patient and receive the observations."""
    case: HadmCase = get_current_case()
    pe = case.physical_exam_text or "No physical exam data available."
    return pe
