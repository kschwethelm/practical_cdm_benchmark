import spacy
from typing import List, Union
import regex as re

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

def keyword_search(s: str, k: str): 
    s = s.lower()
    k = re.escape(k.lower())

    if k not in s:
        return False

    for pattern in NEGATION_PATTERNS:
        neg_regex = pattern.format(k)
        if re.search(neg_regex, s):
            return False
    return True

def keyword_positive(sentence: Union[str, List], keyword: str):
    if isinstance(sentence, list):
        return any(keyword_search(s, keyword) for s in sentence)
    else: 
        return keyword_search(sentence, keyword)

def procedure_checker(valid_procedures: List, done_procedures: List):
    return any(keyword_positive(done_procedures, proc) for proc in valid_procedures)

def alt_procedure_checker(operation_keywords, text):
    for alternative_operations in operation_keywords:
        op_loc = alternative_operations["location"]
        for op_mod in alternative_operations["modifiers"]:
            for sentence in text.split("."):
                if keyword_positive(sentence, op_loc) and keyword_positive(sentence, op_mod):
                    return True
    return False

