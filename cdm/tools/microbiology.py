from langchain.tools import tool

from cdm.benchmark.data_models import HadmCase
from cdm.tools.context import get_current_case


@tool
def request_microbiology(test_name: str) -> str:
    """Return microbiology results for the patient (blood/urine cultures, etc.).

    Args:
        test_name: The microbiology test to request. Use "all" for all results.

    Returns:
        Formatted microbiology results
    """
    case: HadmCase = get_current_case()
    microbio_events = case.microbiology_events

    if not microbio_events:
        return "No microbiology results available for this patient."

    # If "all" is requested, return all microbiology results
    if test_name.lower() == "all":
        result_lines = []
        for bio in microbio_events:
            bio_line = (
                f"- {bio.test_name or 'N/A'} [{bio.spec_type_desc or 'N/A'}]: "
                f"Organism: {bio.organism_name or 'N/A'}"
            )
            if bio.comments:
                bio_line += f" - {bio.comments}"
            if bio.charttime:
                bio_line += f" (Time: {bio.charttime})"
            result_lines.append(bio_line)
        return "\n".join(result_lines)

    # Otherwise, search for specific test
    for bio in microbio_events:
        if test_name.lower() in (bio.test_name or "").lower():
            result = (
                f"- Time collected: {bio.charttime or 'N/A'}\n"
                f"- Specimen type: {bio.spec_type_desc or 'N/A'}\n"
                f"- Test name: {bio.test_name or 'N/A'}\n"
                f"- Organism found: {bio.organism_name or 'N/A'}\n"
                f"- Comments: {bio.comments or 'N/A'}\n"
            )
            return result

    return f"No microbiology result found for test: {test_name}"
