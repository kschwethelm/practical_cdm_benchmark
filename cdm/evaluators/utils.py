import re

from cdm.benchmark.data_models import Treatment

NEGATION_PATTERNS = [
    r"no\s+{}",
    r"not\s+{}",
    r"without\s+{}",
    r"denies\s+{}",
    r"absence\s+of\s+{}",
    r"no\s+evidence\s+of\s+{}",
    r"no\s+signs\s+of\s+{}",
    r"free\s+of\s+{}",
]


def keyword_search(s: str, k: str) -> bool:
    """
    Check whether a keyword is positively mentioned in a sentence.

    The function returns True if the keyword is present in the sentence
    and is not negated by common negation patterns (e.g., "absence of appendicitis", "no signs of pancreatitis").

    :param s: Sentence to search.
    :type s: str
    :param k: Keyword to search for.
    :type k: str
    :return: True if the keyword is present and not negated, False otherwise.
    :rtype: bool
    """
    s = s.lower()
    k = re.escape(k.lower())

    if k not in s:
        return False

    for pattern in NEGATION_PATTERNS:
        neg_regex = pattern.format(k)
        if re.search(neg_regex, s):
            return False
    return True


def extract_procedure_icd_codes(treatments: list) -> list[str]:
    """
    Extract the ICD procedure codes from a list of Treatment objects.

    :param treatments: List containing Treatment objects
    :type treatments: list
    :return: List of ICD codes for Treatment objects with defined codes.
    :rtype: list[str]
    """
    return [p.icd_code for p in treatments if isinstance(p, Treatment) and p.icd_code is not None]


def keyword_positive(sentence: str | list, keyword: str) -> bool:
    """

    Apply positive keyword detection to either a single sentence or a list of sentences.

    :param sentence: Sentence or list of sentences to search.
    :type sentence: str | list
    :param keyword: Keyword to search for.
    :type keyword: str
    :return: True if keyword is present and not negated, False otherwise.
    :rtype: bool
    """
    if isinstance(sentence, list):
        return any(keyword_search(s, keyword) for s in sentence)
    else:
        return keyword_search(sentence, keyword)


def procedure_checker(valid_procedures: list, done_procedures: list) -> bool:
    """
    Check if any of the keywords/ ICD codes associated with a valid treatment are present in the list of requested treatments.

    :param valid_procedures: Keywords/ ICD codes associated with a valid treatment for the pathology.
    :type valid_procedures: list
    :param done_procedures: List of treatments to check against valid_procedures.
    :type done_procedures: list
    :return: True if the valid treatment is present, False otherwise
    :rtype: bool
    """
    done_titles = [
        procedure.title if not isinstance(procedure, str) else procedure
        for procedure in done_procedures
    ]
    return any(keyword_positive(done_titles, proc) for proc in valid_procedures)


def alt_procedure_checker(operation_keywords: list[dict], text) -> bool:
    for alternative_operations in operation_keywords:
        op_loc = alternative_operations["location"]
        for op_mod in alternative_operations["modifiers"]:
            for sentence in text:
                if keyword_positive(sentence, op_loc) and keyword_positive(sentence, op_mod):
                    return True
    return False


def calculate_average(results: list, field: str) -> tuple[float, int]:
    """
    Compute the average score per field across all cases.

    :param results: list of each case's results
    :type results: list
    :param field: the field to calculate the average for
    :type field: str
    :return: average of field; total samples
    :rtype: Tuple[float, int]
    """
    average = 0
    for patient in results:
        average += patient["scores"][field]

    average /= len(results)
    return average, len(results)


def count_unnecessary(results: list, field: str) -> list:
    """
    Counts unnecessary labs or imaging for each case

    :param results: list of each case's results
    :type results: list
    :param field: the field to count
    :type field: str
    :return: the modified list of each case's results with the count added
    :rtype: list
    """
    for patient in results:
        patient["scores"][field] = len(patient["answers"][field])
    return results


def count_treatment(results: list) -> list:
    """
    Computes treatment request accuracy per patient; calculated as # of correctly requested treatments/ # of all required treatments

    :param results: list of each case's results
    :type results: list
    :return: modified list of each case's results with treatment scoring added.
    :rtype: list
    """
    for patient in results:
        required = patient["answers"].get("Treatment Required", {})
        requested = patient["answers"].get("Treatment Requested", {})

        required_true = [k for k, v in required.items() if v]
        if not required_true:
            score = 0.0
        else:
            correct = sum(1 for k in required_true if requested.get(k))
            score = correct / len(required_true)

        patient["scores"]["Treatment Requested"] = score
    return results
