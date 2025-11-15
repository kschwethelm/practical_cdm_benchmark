from langchain.tools import tool

CURRENT_CASE = None  # To be set when loading a case


@tool
def request_physical_exam(system: str) -> str:
    """Return physical exam findings for the requested body system."""
    if CURRENT_CASE is None:
        return "Error: no case loaded."

    pe = CURRENT_CASE.get("physical_exam") or {}

    system = system.lower()

    if system in ["abdominal", "abdomen"]:
        return pe.get("abdominal", "Not documented")
    elif system in ["vitals", "vital signs"]:
        return pe.get("vital_signs", "Not documented")
    elif system in ["general"]:
        return pe.get("general", "Not documented")
    elif system in ["cardiovascular", "cardio", "heart"]:
        return pe.get("cardiovascular", "Not documented")
    elif system in ["neurological", "neurology", "nervous system"]:
        return pe.get("neurological", "Not documented")
    elif system in ["pulmonary", "lungs", "respiratory"]:
        return pe.get("pulmonary", "Not documented")
    elif system in ["heent", "head, eyes, ears, nose, throat", "neck"]:
        return pe.get("heent_neck", "Not documented")
    elif system in ["extremities", "limbs"]:
        return pe.get("extremities", "Not documented")
    elif system in ["skin"]:
        return pe.get("skin", "Not documented")
    else:
        return "No such physical exam system documented."
