from langchain.tools import tool

from cdm.tools.context import get_current_case


def create_microbio_tool():
    @tool
    def request_microbio_test(test_name: str) -> str:
        """Return microbiology results for the patient (blood/urine cultures, etc.)."""
        case = get_current_case()
        bio = case.get("first_microbiology_result")
        if bio:
            result = (
                # f"Microbiology result:\n"
                f"- Time collected: {bio.get('charttime', 'N/A')}\n"
                f"- Specimen type: {bio.get('spec_type_desc', 'N/A')}\n"
                f"- Test name: {bio.get('test_name', 'N/A')}\n"
                f"- Organism found: {bio.get('org_name', 'N/A')}\n"
                f"- Interpretation: {bio.get('interpretation', 'N/A')}\n"
            )
            return result

        # Otherwise, use the new format (list of microbiology events)
        microbio_events = case.get("microbiology_events", [])
        if not microbio_events:
            return "No microbiology results available for this patient."

        # If "all" is requested, return all microbiology results
        if test_name.lower() == "all":
            result_lines = []
            for bio in microbio_events:
                bio_line = (
                    f"- {bio.get('test_name', 'N/A')} [{bio.get('spec_type_desc', 'N/A')}]: "
                    f"Organism: {bio.get('organism_name', 'N/A')}"
                )
                if bio.get("interpretation"):
                    bio_line += f" - {bio.get('interpretation')}"
                if bio.get("charttime"):
                    bio_line += f" (Time: {bio.get('charttime')})"
                result_lines.append(bio_line)
            return "\n".join(result_lines)

        # Otherwise, search for specific test
        for bio in microbio_events:
            if test_name.lower() in bio.get("test_name", "").lower():
                result = (
                    f"- Time collected: {bio.get('charttime', 'N/A')}\n"
                    f"- Specimen type: {bio.get('spec_type_desc', 'N/A')}\n"
                    f"- Test name: {bio.get('test_name', 'N/A')}\n"
                    f"- Organism found: {bio.get('organism_name', 'N/A')}\n"
                    f"- Interpretation: {bio.get('interpretation', 'N/A')}\n"
                )
                return result

        return f"No microbiology result found for test: {test_name}"

    return request_microbio_test
