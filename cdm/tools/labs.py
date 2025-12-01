
from langchain.tools import tool

from cdm.tools.context import get_current_case


def create_lab_tool():
    @tool
    def request_lab_test(test_name: str) -> str:
        """Return lab results based on the patient case."""
        case = get_current_case()
        lab = case.get("first_lab_result")
        if lab:
            result = (
                # f"Lab result:\n"
                f"- Time: {lab.get('charttime')}\n"
                f"- Test ID: {lab.get('itemid', 'N/A')}\n"
                f"- Value: {lab.get('value', 'N/A')}\n"
                f"- Text Value: {lab.get('valueuom', 'N/A')}\n"
                f"- Numeric Value: {lab.get('valuenum', 'N/A')}\n"
            )
            return result

        # Otherwise, use the new format (list of lab results)
        lab_results = case.get("lab_results", [])
        if not lab_results:
            return "No lab results available for this patient."

        # If "all" is requested, return all lab results
        if test_name.lower() == "all":
            result_lines = []
            for lab in lab_results:
                test_line = f"- {lab.get('test_name', 'N/A')}: {lab.get('value', 'N/A')}"
                if lab.get("unit"):
                    test_line += f" {lab.get('unit')}"
                if lab.get("flag"):
                    test_line += f" [{lab.get('flag')}]"
                if (
                    lab.get("ref_range_lower") is not None
                    and lab.get("ref_range_upper") is not None
                ):
                    test_line += (
                        f" (ref: {lab.get('ref_range_lower')}-{lab.get('ref_range_upper')})"
                    )
                result_lines.append(test_line)
            return "\n".join(result_lines)

        # Otherwise, search for the specific test
        for lab in lab_results:
            if test_name.lower() in lab.get("test_name", "").lower():
                result = (
                    f"- Test: {lab.get('test_name', 'N/A')}\n"
                    f"- Value: {lab.get('value', 'N/A')} {lab.get('unit', '')}\n"
                    f"- Flag: {lab.get('flag', 'normal')}\n"
                    f"- Reference Range: {lab.get('ref_range_lower', 'N/A')}-{lab.get('ref_range_upper', 'N/A')}\n"
                )
                return result

        return f"No lab result found for test: {test_name}"

    return request_lab_test
