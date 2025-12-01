from contextvars import ContextVar
from typing import Any

# Global context variable for current case
current_case: ContextVar[dict[str, Any]] = ContextVar("current_case", default=None)


def set_current_case(case: dict[str, Any]) -> None:
    current_case.set(case)


def get_current_case() -> dict[str, Any]:
    case = current_case.get()
    if case is None:
        raise RuntimeError("No case context set. Call set_current_case() first.")
    return case
