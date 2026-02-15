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

TOOL_SPECS = {
    "physical_exam": {"description": "Perform a physical examination", "args": {}},
    "lab": {
        "description": "Request a laboratory or microbiology test",
        "args": {"test_name": "string (e.g. 'CBC', 'CRP', 'Lipase')"},
    },
    "radiology": {
        "description": "Request an imaging study",
        "args": {
            "region": "string (e.g. Abdomen)",
            "modality": "string (e.g.,CT, Ultrasound, MRI, X-ray)",
        },
    },
    "diagnosis_criteria": {
        "description": "Retrieve diagnostic criteria for specific pathology",
        "args": {"pathology": "string (e.g. Appendicitis, Pneumonia)"},
    },
}


__all__ = [
    "get_current_case",
    "set_current_case",
    "request_lab_test",
    "physical_examination",
    "request_imaging",
    "retrieve_diagnosis_criteria",
    "AVAILABLE_TOOLS",
    "TOOL_SPECS",
]
