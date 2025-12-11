from typing import List, Dict
from cdm.benchmark.data_models import (
    AgentRunResult,
    GroundTruth,
    BenchmarkOutputFullInfo,
    Pathology,
)
from thefuzz import fuzz
from cdm.evaluators.utils import keyword_positive


class PathologyEvaluator:
    FUZZY_MATCH_THRESHOLD = 90
    pathology: str = ""
    alternative_pathology_names: List[Dict] = []
    gracious_alternative_pathology_names: List[Dict] = []
    required_lab_tests: Dict[str, List[str]] = {}
    neutral_lab_tests: List[str] = []

    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        self.grounded_treatment = ground_truth.treatments
        self.grounded_diagnosis = ground_truth.primary_diagnosis
        if pathology:
            self.pathology = pathology.value.lower()

        self.answers = {
            "Diagnosis": "",
            "Diagnostic Confidence": None,
            "Treatment": [],
            "Correct Laboratory Tests": {k: [] for k in self.required_lab_tests},
            "Unnecessary Laboratory Tests": [],
            "Neutral Laboratory Tests": [],
            "Correct Imaging": [],
            "Unnecessary Imaging": [],
            "Treatment Requested": {},
            "Treatment Required": {},
        }

        self.scores = {
            "Late Physical Examination": 0,
            "Physical Examination": 0,
            "Laboratory Tests": 0,
            "Imaging": 0,
            "Diagnosis": 0,
            "Gracious Diagnosis": 0,
        }

        self.explanations = {"Imaging": "", "Physical": "", "Diagnosis": ""}

    def evaluate_case(self, output: AgentRunResult | BenchmarkOutputFullInfo):
        if isinstance(output, BenchmarkOutputFullInfo):
            self.answers["Diagnosis"] = output.diagnosis
            self.score_diagnosis()
            evaluation = {
                "Diagnosis": self.scores["Diagnosis"],
                "Gracious Diagnosis": self.scores["Gracious Diagnosis"],
            }
            return evaluation
        else:
            self.answers["Diagnosis"] = output.parsed_output.final_diagnosis
            self.score_diagnosis()

        tool_calls = [
            tc
            for m in output.messages
            if "tool_calls" in m and m["tool_calls"]
            for tc in m["tool_calls"]
        ]
        for idx, tool in enumerate(tool_calls):
            tool_name = tool.get("name")  # tool_calls is a list of dict
            tool_call = tool_calls[idx]
            if tool_name == "physical_examination":
                self.score_physical_exam(idx)
                if not self.explanations["Physical"]:
                    self.explanations["Physical"] = (
                        "PROTOCOL VIOLATION: Physical examination was not ordered"
                    )
                if not self.explanations["Diagnosis"]:
                    self.explanations["Diagnosis"] = (
                        "INCORRECT: Model does not predict the ground truth diagnosis."
                    )
            elif tool_name == "request_imaging":
                self.score_imaging_action(tool_call)
            elif tool_name == "request_lab_test":
                self.score_lab(tool_call)

        self.answers["Treatment"] = output.parsed_output.treatment
        self.score_treatment()

        return self.answers, self.scores

    def score_physical_exam(self, idx: int):
        if idx == 0:  # physical exam is the first tool called
            self.scores["Physical Examination"] = 1
            self.scores["Late Physical Examination"] = 1
            self.explanations["Physical"] = "CORRECT: Physical Exam was ordered first."
        else:
            self.scores["Late Physical Examination"] = 1
            if self.scores["Physical Examination"] == 0:
                self.explanations["Physical"] = (
                    "PROTOCOL VIOLATION: Physical Exam was not ordered first."
                )

    def score_lab(self, tool_call: dict):
        args = tool_call.get("args")
        test_id = args.get("test_id")

        for test_category, valid_test_names in self.required_lab_tests.items():
            if test_id in valid_test_names:
                if len(self.answers["Correct Laboratory Tests"][test_category]) == 0:
                    self.scores["Laboratory Tests"] += 1
                self.answers["Correct Laboratory Tests"][test_category].append(test_id)
                break
        else:
            if test_id in self.neutral_lab_tests:
                self.answers["Unnecessary Laboratory Tests"].append(test_id)

    def score_imaging_action(self, tool_call: dict):
        args = tool_call.get("args")
        modality = args.get("modality").lower()
        region = args.get("region").lower()
        imaging_dict = {"region": region, "modality": modality}

        if (
            not self.score_imaging(region, modality)
            or imaging_dict in self.answers["Correct Imaging"]
        ):
            self.answers["Unnecessary Imaging"].append(imaging_dict)
        else:
            self.answers["Correct Imaging"].append(imaging_dict)

    def score_diagnosis(self):
        answer = self.answers["Diagnosis"].lower()
        for word in answer.split():
            if fuzz.ratio(word, self.pathology) > self.FUZZY_MATCH_THRESHOLD and keyword_positive(
                self.pathology, word
            ):
                self.scores["Diagnosis"] = 1
                self.scores["Gracious Diagnosis"] = 1
                self.explanations["Diagnosis"] = (
                    "CORRECT: Model prediction matches ground truth diagnosis closely."
                )
                return
        for alternative_patho in self.alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if (
                    patho_loc in answer
                    and patho_mod in answer
                    and keyword_positive(answer, patho_loc)
                    and keyword_positive(answer, patho_mod)
                ):
                    self.scores["Diagnosis"] = 1
                    self.scores["Gracious Diagnosis"] = 1
                    self.explanations["Diagnosis"] = (
                        "CORRECT: Model prediction matches alternative name for ground truth diagnosis."
                    )
                    return
        for alternative_patho in self.gracious_alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if (
                    patho_loc in answer
                    and patho_mod in answer
                    and keyword_positive(answer, patho_loc)
                    and keyword_positive(answer, patho_mod)
                ):
                    self.scores["Gracious Diagnosis"] = 1
                    self.explanations["Diagnosis"] = (
                        "ACCEPTABLE: Model prediction is similar to the ground truth diagnosis."
                    )
                    return

    def score_imaging(self, region: str, modality: str) -> bool:
        return

    def score_treatment(self):
        return
