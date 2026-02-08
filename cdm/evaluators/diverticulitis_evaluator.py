from cdm.benchmark.data_models import GroundTruth, Pathology
from cdm.evaluators.mappings import (
    ALTERNATE_COLECTOMY_KEYWORDS,
    ALTERNATE_DRAINAGE_KEYWORDS_DIVERTICULITIS,
    COLECTOMY_PROCEDURES_ICD9,
    COLECTOMY_PROCEDURES_ICD10,
    COLECTOMY_PROCEDURES_KEYWORDS,
    DRAINAGE_LOCATIONS_DIVERTICULITIS,
    DRAINAGE_PROCEDURES_ALL_ICD10,
    DRAINAGE_PROCEDURES_ICD9,
    DRAINAGE_PROCEDURES_KEYWORDS,
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


class DiverticulitisEvaluator(PathologyEvaluator):
    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        super().__init__(ground_truth, pathology)
        self.pathology = "diverticulitis"
        self.alternative_pathology_names = [
            {
                "location": "diverticul",
                "modifiers": [
                    "infect",
                    "inflam",
                    "abscess",
                    "rupture",
                    "perf",
                ],
            }
        ]
        self.gracious_alternative_pathology_names = [
            {
                "location": "acute colonic",
                "modifiers": ["perfor"],
            },
            {
                "location": "sigmoid",
                "modifiers": ["perfor"],
            },
            {
                "location": "sigmoid",
                "modifiers": ["colitis"],
            },
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
            "Colonoscopy": False,
            "Antibiotics": False,
            "Support": False,
            "Drainage": False,
            "Colectomy": False,
        }
        self.answers["Treatment Required"] = {
            "Colonoscopy": True,
            "Antibiotics": True,
            "Support": True,
            "Drainage": False,
            "Colectomy": False,
        }

    def score_imaging(self, region: str, modality: str):
        if region == "abdomen":
            if modality == "ct":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 2
                    self.explanations["Imaging"] = (
                        "CORRECT: Preferred imaging modality was ordered (CT) in the correct order"
                    )
                return True
            if modality == "ultrasound" or modality == "us" or modality == "mri":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = (
                        f"ACCEPTABLE: {modality} is acceptable but should not be done before CT"
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

        if keyword_positive(self.answers["Treatment"], "colonoscopy"):
            self.answers["Treatment Requested"]["Colonoscopy"] = True

        if keyword_positive(self.answers["Treatment"], "antibiotic"):
            self.answers["Treatment Requested"]["Antibiotics"] = True
        if (
            keyword_positive(self.answers["Treatment"], "fluid")
            or keyword_positive(self.answers["Treatment"], "analgesi")
            or keyword_positive(self.answers["Treatment"], "pain")
        ):
            self.answers["Treatment Requested"]["Support"] = True

        if (
            any(code in DRAINAGE_PROCEDURES_ICD9 for code in procedure_icd_codes)
            or any(code in DRAINAGE_PROCEDURES_ALL_ICD10 for code in procedure_icd_codes)
            or (
                procedure_checker(DRAINAGE_PROCEDURES_KEYWORDS, self.grounded_treatment)
                and procedure_checker(DRAINAGE_LOCATIONS_DIVERTICULITIS, self.grounded_treatment)
            )
        ):
            self.answers["Treatment Required"]["Drainage"] = True

        if alt_procedure_checker(
            ALTERNATE_DRAINAGE_KEYWORDS_DIVERTICULITIS, self.answers["Treatment"]
        ):
            self.answers["Treatment Requested"]["Drainage"] = True

        if (
            any(code in COLECTOMY_PROCEDURES_ICD9 for code in procedure_icd_codes)
            or any(code in COLECTOMY_PROCEDURES_ICD10 for code in procedure_icd_codes)
            or procedure_checker(COLECTOMY_PROCEDURES_KEYWORDS, self.grounded_treatment)
        ):
            self.answers["Treatment Required"]["Colectomy"] = True

        if procedure_checker(
            COLECTOMY_PROCEDURES_KEYWORDS, self.answers["Treatment"]
        ) or alt_procedure_checker(ALTERNATE_COLECTOMY_KEYWORDS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["Colectomy"] = True
