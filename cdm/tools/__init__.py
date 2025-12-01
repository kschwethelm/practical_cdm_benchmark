from .context import get_current_case, set_current_case
from .labs import request_lab_test
from .microbiology import request_microbio_test
from .physical_exam import physical_examination
from .radiology import request_imaging

# Registry of all available tools
AVAILABLE_TOOLS = {
    "physical_exam": physical_examination,
    "lab": request_lab_test,
    "microbiology": request_microbio_test,
    "radiology": request_imaging,
}

__all__ = [
    "request_lab_test",
    "request_microbio_test",
    "physical_examination",
    "request_imaging",
    "AVAILABLE_TOOLS",
    "set_current_case",
    "get_current_case",
]
