from typing import List 
from cdm.evaluators.pathology_evaluator import PathologyEvaluator
from cdm.evaluators.mappings import INFLAMMATION_LAB_TESTS, CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, ALTERNATE_CHOLECYSTECTOMY_KEYWORDS
from cdm.evaluators.mappings import ADDITIONAL_LAB_TEST_MAPPING as LAB_MAP
from cdm.evaluators.utils import procedure_checker, keyword_positive, alt_procedure_checker

class CholecystitisEvaluator(PathologyEvaluator): 
    def __init__(self, grounded_treatment: List[str], grounded_diagnosis: str, hadm_id: int):
        super().__init__(grounded_treatment, grounded_diagnosis, hadm_id) 
        self.pathology = "cholecystitis"
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
            'Inflammation': INFLAMMATION_LAB_TESTS, 
            'Liver': [
                50861,  # "Alanine Aminotransferase (ALT)",
                50878,  # "Asparate Aminotransferase (AST)",
            ],
            'Gallbladder': [
                50883,  # "Bilirubin",
                50927,  # "Gamma Glutamyltransferase",
            ]}
        neutral_labs = ['Complete Blood Count (CBC)', 'Renal Function Panel (RFP)', 'Urinalysis']
        for lab in neutral_labs: 
            self.neutral_lab_tests += LAB_MAP[lab]
        self.neutral_lab_tests = [lab for lab in self.neutral_lab_tests 
                                  if lab not in self.required_lab_tests['Inflammation'] 
                                  and lab not in self.required_lab_tests['Liver'] 
                                  and lab not in self.required_lab_tests['Gallbladder']]
        
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
                    self.explanations["Imaging"] = f"CORRECT: Preferred imaging modality was ordered ({modality}) in the correct order"
                return True
            if modality == "mri" or modality == "eus":
                if self.scores["Imaging"] == 0:
                    self.scores["Imaging"] = 1
                    self.explanations["Imaging"] = f"ACCEPTABLE: {modality} is acceptable but should not be done before US/HIDA"
                return True
            self.explanations["Imaging"] = "INCORRECT MODALITY: None of US/HIDA/MRI/EUS imaging were ordered"
        else: 
            self.explanations["Imaging"] = "INCORRECT REGION: Only abdomen should be imaged"
        return False
    
    def score_treatment(self):
        if procedure_checker(CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, self.grounded_treatment):
            self.answers["Treatment Required"]["Cholecystectomy"] = True

        if procedure_checker(CHOLECYSTECTOMY_PROCEDURES_KEYWORDS, self.answers["Treatment"]) or \
            alt_procedure_checker(ALTERNATE_CHOLECYSTECTOMY_KEYWORDS, self.answers["Treatment"]):
            self.answers["Treatment Requested"]["Cholecystectomy"] = True

        if (keyword_positive(self.answers["Treatment"], "fluid")
            or keyword_positive(self.answers["Treatment"], "analgesi")
            or keyword_positive(self.answers["Treatment"], "pain")
        ):
            self.answers["Treatment Requested"]["Support"] = True

        if keyword_positive(self.answers["Treatment"], "antibiotic"):
            self.answers["Treatment Requested"]["Antibiotics"] = True
        
        
        