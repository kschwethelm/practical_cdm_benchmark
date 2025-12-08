from typing import List
from cdm.evaluators.pathology_evaluator import PathologyEvaluator
from cdm.evaluators.mappings import INFLAMMATION_LAB_TESTS, DRAINAGE_PROCEDURES_KEYWORDS, DRAINAGE_LOCATIONS_PANCREATITIS, \
    ALTERNATE_DRAINAGE_KEYWORDS_PANCREATITIS, ERCP_PROCEDURES_KEYWORDS, CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, \
        ALTERNATE_CHOLECYSTECTOMY_KEYWORDS
from cdm.evaluators.mappings import ADDITIONAL_LAB_TEST_MAPPING as LAB_MAP
from cdm.evaluators.utils import procedure_checker, keyword_positive, alt_procedure_checker
from cdm.benchmark.data_models import GroundTruth, Pathology

class PancreatitisEvaluator(PathologyEvaluator): 
    def __init__(self, ground_truth: GroundTruth, pathology: Pathology):
        super().__init__(ground_truth, pathology) 
        self.pathology = "pancreatitis"
        self.alternative_pathology_names = [
            {
                "location": "pancrea",
                "modifiers": [
                    "gangren",
                    "infect",
                    "inflam",
                    "abscess",
                    "necros",
                ],
            }
        ]
        
        self.required_lab_tests = {
            'Inflammation': INFLAMMATION_LAB_TESTS, 
            'Pancreas': [
                50867,  # Amylase
                50956,  # Lipase
            ],
            'Seriousness': [
                51480,  # "Hematocrit",
                50810,
                51221,
                51638,
                51006,  # "Urea Nitrogen",
                52647,
                51000,  # "Triglycerides",
                50893,  # "Calcium, Total",
                50824,  # "Sodium",
                52623,
                50983,
                52610,  # "Potassium",
                50971,
                50822,
            ]}
        neutral_labs = ['Complete Blood Count (CBC)', 'Liver Function Panel (LFP)', 'Renal Function Panel (RFP)', 'Urinalysis']
        for lab in neutral_labs: 
            self.neutral_lab_tests += LAB_MAP[lab]
        self.neutral_lab_tests = [lab for lab in self.neutral_lab_tests if 
                                  lab not in self.required_lab_tests['Inflammation'] and 
                                  lab not in self.required_lab_tests['Pancreas'] and 
                                  lab not in self.required_lab_tests['Seriousness']]

        self.answers["Treatment Requested"] = {
            "Support": False,
            "Drainage": False,
            "ERCP": False,
            "Cholecystectomy": False,
        }
        self.answers["Treatment Required"] = {
            "Support": True,
            "Drainage": False,
            "ERCP": False,
            "Cholecystectomy": False,
        }
        
    def score_imaging(self, region: str, modality: str):
        if region == "abdomen":
            if modality == "ultrasound" or modality == "us":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 2
                    self.explanations["Imaging"] = "CORRECT: Preferred imaging modality was ordered (Ultrasound) in the correct order"

                return True
            if modality == "ct":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = "ACCEPTABLE: CT is acceptable but should not be done before US"

                return True
            if modality == "eus":
                if keyword_positive(self.grounded_diagnosis, "biliary"):
                    self.scores["Imaging"] += 1
                    self.explanations["Imaging"] = "ACCEPTABLE: EUS is acceptable if patient has biliary etiology"

                return True
        return False
    
    def score_treatment(self):
        if (keyword_positive(self.answers["Treatment"], "fluid")
            and (keyword_positive(self.answers["Treatment"], "analgesi")
                or keyword_positive(self.answers["Treatment"], "pain"))
            and keyword_positive(self.answers["Treatment"], "monitor")
        ):
            self.answers["Treatment Requested"]["Support"] = True

        if (procedure_checker(DRAINAGE_PROCEDURES_KEYWORDS, self.grounded_treatment)
                and procedure_checker(DRAINAGE_LOCATIONS_PANCREATITIS, self.grounded_treatment)):
            self.answers["Treatment Required"]["Drainage"] = True

        if alt_procedure_checker(ALTERNATE_DRAINAGE_KEYWORDS_PANCREATITIS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["Drainage"] = True

        if keyword_positive(self.grounded_diagnosis, "biliary"):
            self.answers["Treatment Required"]["Cholecystectomy"] = True
            if procedure_checker(CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, self.answers["Treatment"]) or \
                alt_procedure_checker(ALTERNATE_CHOLECYSTECTOMY_KEYWORDS, self.answers["Treatment"]):
                self.answers["Treatment Requested"]["Cholecystectomy"] = True

        if (procedure_checker(ERCP_PROCEDURES_KEYWORDS, self.grounded_treatment)):
            self.answers["Treatment Required"]["ERCP"] = True

        if procedure_checker(ERCP_PROCEDURES_KEYWORDS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["ERCP"] = True
        
        
        