from cdm.benchmark.data_models import GroundTruth, Pathology
from cdm.evaluators.mappings import (
    ALTERNATE_APPENDECTOMY_KEYWORDS,
    APPENDECTOMY_PROCEDURES_ICD9,
    APPENDECTOMY_PROCEDURES_ICD10,
    APPENDECTOMY_PROCEDURES_KEYWORDS,
    INFLAMMATION_LAB_TESTS,
)
from cdm.evaluators.pathology_evaluator import PathologyEvaluator
from cdm.evaluators.utils import (
    alt_procedure_checker,
    extract_procedure_icd_codes,
    keyword_positive,
    procedure_checker,
)
from cdm.tools.lab_mappings import ADDITIONAL_LAB_TEST_MAPPING as LAB_MAP


class AppendicitisEvaluator(PathologyEvaluator):
    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        super().__init__(ground_truth, pathology)
        self.pathology = "appendicitis"
        self.alternative_pathology_names = [
            {
                "location": "appendi",
                "modifiers": [
                    "gangren",
                    "infect",
                    "inflam",
                    "abscess",
                    "rupture",
                    "necros",
                    "perf",
                ],
            }
        ]

        self.required_lab_tests = {"Inflammation": INFLAMMATION_LAB_TESTS}

        self.neutral_lab_tests = {
            "Complete Blood Count (CBC)": LAB_MAP["Complete Blood Count (CBC)"],
            "Liver Function Panel (LFP)": LAB_MAP["Liver Function Panel (LFP)"],
            "Renal Function Panel (RFP)": LAB_MAP["Renal Function Panel (RFP)"],
            "Urinalysis": LAB_MAP["Urinalysis"],
        }

        all_required = {t for cat_tests in self.required_lab_tests.values() for t in cat_tests}
        self.neutral_lab_tests = {
            category: [lab for lab in labs if lab not in all_required]
            for category, labs in self.neutral_lab_tests.items()
        }
        self.answers["Correct Laboratory Tests"] = {k: False for k in self.required_lab_tests}
        self.answers["Neutral Laboratory Tests"] = {k: False for k in self.neutral_lab_tests}

        self.answers["Treatment Requested"] = {
            "Appendectomy": False,
            "Antibiotics": False,
            "Support": False,
        }
        self.answers["Treatment Required"] = {
            "Appendectomy": False,
            "Antibiotics": True,
            "Support": True,
        }

    def score_imaging(self, region: str, modality: str):
        if region == "abdomen":
            # TODO: Score according to what was done in case and not blindly following guidelines? i.e. if only CT was done by Dr, then give full points
            if modality == "ultrasound" or modality == "us":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 2
                    self.explanations["Imaging"] = (
                        "CORRECT: Preferred imaging modality was ordered (Ultrasound) in the correct order"
                    )
                return True

            if modality == "ct":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = (
                        "ACCEPTABLE: CT is acceptable but should not be done before US"
                    )
                return True

            if modality == "mri":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = (
                        "ACCEPTABLE: MRI is acceptable but should not be done before US (preferred to CT for pregnant patients)"
                    )
                return True
            self.explanations["Imaging"] = (
                "INCORRECT MODALITY: None of US/MRI/CT imaging were ordered"
            )
        else:
            self.explanations["Imaging"] = "INCORRECT REGION: Only abdomen should be imaged"
        return False

    def score_treatment(self):
        procedure_icd_codes = extract_procedure_icd_codes(self.grounded_treatment)
        if (
            any(code in APPENDECTOMY_PROCEDURES_ICD10 for code in procedure_icd_codes)
            or any(code in APPENDECTOMY_PROCEDURES_ICD9 for code in procedure_icd_codes)
            or procedure_checker(APPENDECTOMY_PROCEDURES_KEYWORDS, self.grounded_treatment)
        ):
            self.answers["Treatment Required"]["Appendectomy"] = True

        if procedure_checker(
            APPENDECTOMY_PROCEDURES_KEYWORDS, self.answers["Treatment"]
        ) or alt_procedure_checker(ALTERNATE_APPENDECTOMY_KEYWORDS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["Appendectomy"] = True

        if keyword_positive(self.answers["Treatment"], "antibiotic"):
            self.answers["Treatment Requested"]["Antibiotics"] = True

        if (
            keyword_positive(self.answers["Treatment"], "fluid")
            or keyword_positive(self.answers["Treatment"], "analgesi")
            or keyword_positive(self.answers["Treatment"], "pain")
        ):
            self.answers["Treatment Requested"]["Support"] = True
