import json
import re

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


def keyword_positive(sentence: str | list, keyword: str):
    if isinstance(sentence, list):
        return any(keyword_search(s, keyword) for s in sentence)
    else:
        return keyword_search(sentence, keyword)


def procedure_checker(valid_procedures: list, done_procedures: list):
    done_titles = [
        procedure.title if not isinstance(procedure, str) else procedure
        for procedure in done_procedures
    ]
    return any(keyword_positive(done_titles, proc) for proc in valid_procedures)


def alt_procedure_checker(operation_keywords, text):
    for alternative_operations in operation_keywords:
        op_loc = alternative_operations["location"]
        for op_mod in alternative_operations["modifiers"]:
            for sentence in text:
                if keyword_positive(sentence, op_loc) and keyword_positive(sentence, op_mod):
                    return True
    return False


def calculate_avergae(results: list, field: str):
    average = 0
    for patient in results:
        average += patient["scores"][field]

    average /= len(results)
    return average, len(results)


def count_unnecessary(results: list, field: str):
    for patient in results:
        patient["scores"][field] = len(patient["answers"][field])
    return results


def output_evaluation(output_path: str):
    # for model in models:
    results = {}
    fields = []
    with open(output_path) as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                if not fields:
                    fields = list(obj.get("scores").keys())
                    if "answers" in obj:
                        fields += ["Unnecessary Laboratory Tests", "Unnecessary Imaging"]
                if obj.get("pathology") in results.keys():
                    results[obj.get("pathology")].append(obj)
                else:
                    results[obj.get("pathology")] = [obj]
    if not results:
        print("No records in JSONL file.")
        return

    avg_scores = {}
    avg_samples = {}
    for field in fields:
        avg_scores[field] = {}
        avg_samples[field] = {}
        for pathology in ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]:
            if pathology in results.keys():
                if field in ["Unnecessary Laboratory Tests", "Unnecessary Imaging"]:
                    results[pathology] = count_unnecessary(results[pathology], field)
                avg, n = calculate_avergae(results[pathology], field)
                avg_scores[field][pathology] = avg
                avg_samples[field][pathology] = n
    return avg_scores, avg_samples


# if __name__ == "__main__":
#     print(output_evaluation('./outputs/results_full_info.jsonl'))
