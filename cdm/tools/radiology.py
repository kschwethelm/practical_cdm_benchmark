from typing import Any

from langchain.tools import tool


def create_radiology_tool(case: dict[str, Any]):
    @tool
    def request_imaging(region: str, modality: str) -> str:
        """Request imaging results for a specific scan region and modality.

        Args:
            region: The body region to scan (e.g., 'chest', 'abdomen', 'head')
            modality: The imaging type (e.g., 'CT', 'X-ray', 'MRI', 'ultrasound')

        Returns:
            Imaging results or "No imaging available" message
        """
        imaging_results = case.get("radiology_reports", [])

        if not imaging_results:
            return "No imaging results available for this patient."

        # Search for matching imaging by region and modality
        for imaging in imaging_results:
            img_region = imaging.get("region", "").lower()
            img_modality = imaging.get("modality", "").lower()

            if region.lower() in img_region and modality.lower() in img_modality:
                result = (
                    f"- Region: {imaging.get('region', 'N/A')}\n"
                    f"- Modality: {imaging.get('modality', 'N/A')}\n"
                    f"- Findings: {imaging.get('findings', 'N/A')}\n"
                )
                return result

        return f"No imaging result found for {region} {modality}."

    return request_imaging
