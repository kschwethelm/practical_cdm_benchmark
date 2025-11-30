from .labs import create_lab_tool
from .microbiology import create_microbio_tool
from .physical_exam import create_physical_exam_tool
from .radiology import create_radiology_tool

# Registry of all available tools
AVAILABLE_TOOLS = {
    "physical_exam": create_physical_exam_tool,
    "lab": create_lab_tool,
    "microbiology": create_microbio_tool,
    "radiology": create_radiology_tool,
}

__all__ = [
    "create_lab_tool",
    "create_microbio_tool",
    "create_physical_exam_tool",
    "create_radiology_tool",
    "AVAILABLE_TOOLS",
]
