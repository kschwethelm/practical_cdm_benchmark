"""Medical knowledge retrieval tool using local .j2 files."""

from langchain.tools import tool

from cdm.prompts.utils import (
    get_all_diagnosis_criteria,
    get_diagnosis_criteria,
)


@tool
def retrieve_diagnosis_criteria(pathology: str) -> str:
    """Retrieve diagnosis criteria for a specific condition.

    Args:
        pathology: The condition to look up. Supported conditions:
                   'pancreatitis', 'appendicitis', 'cholecystitis', 'diverticulitis'

    Returns:
        Diagnosis criteria for the specified condition
    """
    criteria = get_diagnosis_criteria(pathology)
    if criteria:
        return f"Diagnosis criteria for {pathology}:\n{criteria}"

    # List available pathologies if not found
    available = list(get_all_diagnosis_criteria().keys())
    return f"No diagnosis criteria found for '{pathology}'. Available: {', '.join(available)}"
