from contextvars import ContextVar

from cdm.benchmark.data_models import HadmCase

# Global context variable for current case
current_case: ContextVar[HadmCase | None] = ContextVar("current_case", default=None)


def set_current_case(case: HadmCase) -> None:
    """Set the current case for tool access."""
    current_case.set(case)


def get_current_case() -> HadmCase:
    """Get the current case. Raises ValueError if no case is set."""
    case = current_case.get()
    if case is None:
        raise ValueError("No case currently set. Call set_current_case() first.")
    return case
