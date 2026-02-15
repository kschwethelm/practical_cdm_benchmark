from thefuzz import fuzz

from cdm.benchmark.data_models import (
    AgentRunResult,
    BenchmarkOutputFullInfo,
    GroundTruth,
    Pathology,
)
from cdm.evaluators.utils import keyword_positive
from cdm.tools.lab_utils import (
    convert_labs_to_itemid,
    load_lab_test_mapping,
    parse_lab_tests_action_input,
)

LAB_TEST_MAPPING_DF = load_lab_test_mapping()


class PathologyEvaluator:
    """
    Base evaluator class that implements evaluation pipeline + general evaluation for diagnosis and labs.
    Subclasses define how imaging and treatments are evaluated.
    """

    FUZZY_MATCH_THRESHOLD = 90
    pathology: str = ""
    alternative_pathology_names: list[dict] = []
    gracious_alternative_pathology_names: list[dict] = []
    required_lab_tests: dict[str, list[str]] = {}
    neutral_lab_tests: list[int] = []

    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        """
        Initialize evaluator with ground truth data and ground truth pathology.

        :param ground_truth: Ground truth diagnosis and treatments.
        :type ground_truth: GroundTruth
        :param pathology: Pathology corresponding to evaluator type.
        :type pathology: Pathology
        """
        self.grounded_treatment = ground_truth.treatments
        self.grounded_diagnosis = ground_truth.primary_diagnosis
        if pathology:
            self.pathology = pathology.value.lower()

        self.answers = {
            "Diagnosis": "",
            "Diagnostic Confidence": None,
            "Treatment": [],
            "Correct Laboratory Tests": {},
            "Neutral Laboratory Tests": {},
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

    def evaluate_case(self, output: AgentRunResult | BenchmarkOutputFullInfo) -> tuple[dict, dict]:
        """
        Evaluate model's predictions for a single case against ground truth.

        :param output: Model's output (either final prediction, or a tool call)
        :type output: AgentRunResult | BenchmarkOutputFullInfo
        :return: Answers and scores for diagnosis accuracy + tool calling, if available
        :rtype: tuple[dict, dict]
        """
        if isinstance(output, BenchmarkOutputFullInfo):
            self.answers["Diagnosis"] = output.diagnosis
            self.score_diagnosis()
            self.answers["Treatment"] = output.treatment
            self.score_treatment()
            full_info_scores = {
                "Diagnosis": self.scores["Diagnosis"],
                "Gracious Diagnosis": self.scores["Gracious Diagnosis"],
            }
            return self.answers, full_info_scores
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
        """
        Score physical exam tool.

        :param idx: Index of the tool call in the sequence of tool calls made by model.
        :type idx: int
        """
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
        """
        Score lab tool call.

        :param tool_call: the tool call made by the model, contains the name of the lab requested.
        :type tool_call: dict
        """
        args = tool_call.get("args")
        test_name = args.get("test_name")
        test_names = parse_lab_tests_action_input(test_name)
        test_ids = convert_labs_to_itemid(test_names, LAB_TEST_MAPPING_DF)

        numeric_ids = {t for t in test_ids if isinstance(t, int)}

        for test_category, valid_test_names in self.required_lab_tests.items():
            matched_ids = numeric_ids & set(valid_test_names)

            if matched_ids:
                if not self.answers["Correct Laboratory Tests"][test_category]:
                    self.scores["Laboratory Tests"] += 1
                self.answers["Correct Laboratory Tests"][test_category] = True

        for test_category, valid_test_names in self.neutral_lab_tests.items():
            matched_ids = numeric_ids & set(valid_test_names)
            if matched_ids:
                self.answers["Neutral Laboratory Tests"][test_category] = True

    def score_imaging_action(self, tool_call: dict):
        """
        Check whether imaging requested was necessary.

        :param tool_call: the tool call made by the model, contains the modality of the imaging and the region to image.
        :type tool_call: dict
        """
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
        """
        Check whether predicted diagnosis matches ground truth diagnosis, and to what degree.

        """
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
        """
        Score the imaging based on what modality was requested and if the imaged region is correct.

        :param region: Requested region to image (e.g., "Abdomen")
        :type region: str
        :param modality: Requested imaging modality (e.g., "US", "CT", etc)
        :type modality: str
        :return: return True if correct region and one of correct modalities (even if not preferred modality)
        :rtype: bool
        """
        return

    def score_treatment(self):
        """
        Score the treatments requested based on necessity and correctness.
        """
        return
