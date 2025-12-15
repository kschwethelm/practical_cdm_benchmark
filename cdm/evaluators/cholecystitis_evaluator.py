from cdm.benchmark.data_models import GroundTruth, Pathology, Treatment
from cdm.evaluators.mappings import (
    ALTERNATE_CHOLECYSTECTOMY_KEYWORDS,
    CHOLECYSTECTOMY_PROCEDURES_ICD9,
    CHOLECYSTECTOMY_PROCEDURES_ICD10,
    CHOLECYSTECTOMY_PROCEDURES_KEYWORDS,
    INFLAMMATION_LAB_TESTS,
)
from cdm.evaluators.pathology_evaluator import PathologyEvaluator
from cdm.evaluators.utils import alt_procedure_checker, keyword_positive, procedure_checker
from cdm.tools.lab_mappings import ADDITIONAL_LAB_TEST_MAPPING as LAB_MAP


class CholecystitisEvaluator(PathologyEvaluator):
    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        super().__init__(ground_truth, pathology)
        self.pathology = "cholecystitis"  # safe fail
        self.alternative_pathology_names = [
            {
                "location": "gallbladder",
                "modifiers": [
                    "gangren",
                    "infect",
                    "inflam",
                    "abscess",
                    "necros",
                    "perf",
                ],
            }
        ]

        self.required_lab_tests = {
            "Inflammation": INFLAMMATION_LAB_TESTS,
            "Liver": [
                50861,  # "Alanine Aminotransferase (ALT)",
                50878,  # "Asparate Aminotransferase (AST)",
            ],
            "Gallbladder": [
                50883,  # "Bilirubin",
                50927,  # "Gamma Glutamyltransferase",
            ],
        }
        neutral_labs = ["Complete Blood Count (CBC)", "Renal Function Panel (RFP)", "Urinalysis"]
        for lab in neutral_labs:
            self.neutral_lab_tests += LAB_MAP[lab]
        self.neutral_lab_tests = [
            lab
            for lab in self.neutral_lab_tests
            if lab not in self.required_lab_tests["Inflammation"]
            and lab not in self.required_lab_tests["Liver"]
            and lab not in self.required_lab_tests["Gallbladder"]
        ]

        self.answers["Treatment Requested"] = {
            "Cholecystectomy": False,
            "Antibiotics": False,
            "Support": False,
        }
        self.answers["Treatment Required"] = {
            "Cholecystectomy": False,
            "Antibiotics": True,
            "Support": True,
        }

    def score_imaging(self, region: str, modality: str):
        if region == "abdomen":
            if modality == "ultrasound" or modality == "us" or modality == "hida":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 2
                    self.explanations["Imaging"] = (
                        f"CORRECT: Preferred imaging modality was ordered ({modality}) in the correct order"
                    )
                return True
            if modality == "mri" or modality == "eus":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = (
                        f"ACCEPTABLE: {modality} is acceptable but should not be done before US/HIDA"
                    )
                return True
            self.explanations["Imaging"] = (
                "INCORRECT MODALITY: None of US/HIDA/MRI/EUS imaging were ordered"
            )
        else:
            self.explanations["Imaging"] = "INCORRECT REGION: Only abdomen should be imaged"
        return False

    def score_treatment(self):
        procedure_icd_codes = [
            p.icd_code
            for p in self.grounded_treatment
            if isinstance(p, Treatment) and p.icd_code is not None
        ]
        if (
            any(code in CHOLECYSTECTOMY_PROCEDURES_ICD10 for code in procedure_icd_codes)
            or any(code in CHOLECYSTECTOMY_PROCEDURES_ICD9 for code in procedure_icd_codes)
            or procedure_checker(CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, self.grounded_treatment)
        ):
            self.answers["Treatment Required"]["Cholecystectomy"] = True

        if procedure_checker(
            CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, self.answers["Treatment"]
        ) or alt_procedure_checker(ALTERNATE_CHOLECYSTECTOMY_KEYWORDS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["Cholecystectomy"] = True

        if (
            keyword_positive(self.answers["Treatment"], "fluid")
            or keyword_positive(self.answers["Treatment"], "analgesi")
            or keyword_positive(self.answers["Treatment"], "pain")
        ):
            self.answers["Treatment Requested"]["Support"] = True

        if keyword_positive(self.answers["Treatment"], "antibiotic"):
            self.answers["Treatment Requested"]["Antibiotics"] = True
