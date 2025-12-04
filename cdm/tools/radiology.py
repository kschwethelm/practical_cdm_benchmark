from langchain.tools import tool

from cdm.benchmark.data_models import HadmCase
from cdm.tools.context import get_current_case


@tool
def request_imaging(region: str, modality: str) -> str:
    """Request imaging results for a specific scan region and modality.

    Args:
        region: The body region to scan (e.g., 'chest', 'abdomen', 'head')
        modality: The imaging type (e.g., 'CT', 'X-ray', 'MRI', 'ultrasound')

    Returns:
        Imaging results or "No imaging available" message
    """
    case: HadmCase = get_current_case()
    imaging_results = case.radiology_reports

    if not imaging_results:
        return "No imaging results available for this patient."

    # Search for matching imaging by region and modality
    for imaging in imaging_results:
        img_region = (imaging.region or "").lower()
        img_modality = (imaging.modality or "").lower()

        if region.lower() in img_region and modality.lower() in img_modality:
            result = (
                f"- Exam Name: {imaging.exam_name or 'N/A'}\n"
                f"- Region: {imaging.region or 'N/A'}\n"
                f"- Modality: {imaging.modality or 'N/A'}\n"
                f"- Findings: {imaging.findings or 'N/A'}\n"
            )
            return result

    return f"No imaging result found for {region} {modality}."
