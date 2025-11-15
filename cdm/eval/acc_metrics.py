import re

def normalize_diagnosis(dx: str) -> str:
    """
    Simple normalization:
    - lowercase
    - key word mapping to 4 classes: appendicitis, cholecystitis, diverticulitis, pancreatitis
    - anything else -> "other"
    """

    if dx is None:
        return "other"

    # lowercase
    dx = dx.lower()

    # core keyword mapping
    if "appendicit" in dx:      
        return "appendicitis"
    if "cholecyst" in dx:       
        return "cholecystitis"
    if "diverticul" in dx:      
        return "diverticulitis"
    if "pancreat" in dx:      
        return "pancreatitis"

    return "other"


def diagnoses_match(gt: str, pred: str) -> bool:
    """Return True if ground truth and prediction match after normalization."""

    return normalize_diagnosis(gt) == pred