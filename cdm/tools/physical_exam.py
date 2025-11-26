from typing import Any

from langchain.tools import tool


def create_physical_exam_tool(case: dict[str, Any]):
    @tool
    def physical_examination() -> str:
        """Perform physical examination of patient and receive the observations."""
        pe = case.get("physical_exam_text", "No physical exam data available.")
        return pe

    return physical_examination
