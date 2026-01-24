from cdm.tools.context import get_current_case, set_current_case
from cdm.tools.diagnosis_criteria import retrieve_diagnosis_criteria
from cdm.tools.labs import request_lab_test
from cdm.tools.physical_exam import physical_examination
from cdm.tools.radiology import request_imaging

AVAILABLE_TOOLS = {
    "physical_exam": physical_examination,
    "lab": request_lab_test,
    "radiology": request_imaging,
    "diagnosis_criteria": retrieve_diagnosis_criteria,
}

__all__ = [
    "get_current_case",
    "set_current_case",
    "request_lab_test",
    "physical_examination",
    "request_imaging",
    "retrieve_diagnosis_criteria",
    "AVAILABLE_TOOLS",
]
