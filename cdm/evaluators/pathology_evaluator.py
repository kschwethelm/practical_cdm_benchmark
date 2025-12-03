from langchain_core.agents import AgentAction
from typing import List, Dict, Tuple, Union
import re
from cdm.benchmark.data_models import AgentRunResult
from thefuzz import fuzz
from abc import abstractmethod
import pandas as pd
import os 

class PathologyEvaluator():

    pathology: str = ""
    alternative_pathology_names: List[Dict] = []
    gracious_alternative_pathology_names: List[Dict] = []
    required_lab_tests: Dict[str, List[str]] = {}
    neutral_lab_tests: List[str] = []
    grounded_treatment: List[str] = [] 
    grounded_diagnosis: str = ""

    def __init__(self, grounded_treatment: List[str], grounded_diagnosis: str, hadm_id: int):
        self.grounded_treatment = grounded_treatment
        self.grounded_diagnosis = grounded_diagnosis
        self.hadm_id = hadm_id
        self.answers = {
            "Diagnosis": "",
            "Treatment": [],
            "Correct Laboratory Tests": {k: [] for k in self.required_lab_tests},
            "Unnecessary Laboratory Tests": [],
            "Neutral Laboratory Tests": [], 
            "Correct Imaging": [],
            "Unnecessary Imaging": [],
            "Treatment Requested": {}, 
            "Treatment Required": {}
        }

        self.scores = {
            "Physical Examination": 0,
            "Late Physical Examination": 0,
            "Laboratory Tests": 0,
            "Imaging": 0,
            "Diagnosis": 0,
            "Gracious Diagnosis": 0,
            "Tool Calls": 0,
        } 
        
        self.explanations = {
            "Imaging": "", 
            "Physical": "", 
            "Diagnosis": ""
        }
    def evaluate_case(self, output: AgentRunResult):
        tool_calls = [m['tool_calls'][0] for m in output.messages if "tool_calls" in m and m["tool_calls"]]
        tools = [m for m in output.messages if m.get("type") == "tool"]
        assert(len(tool_calls) == len(tools))
        for idx, tool in enumerate(tools):
            tool_name = tool.get("name") #tool_calls is a list of dict
            tool_call = tool_calls[idx]
            if tool_name == "physical_examination":
                self.score_physical_exam(idx)
            elif tool_name == "request_imaging":
                self.score_imaging_action(tool_call)
            elif tool_name == "request_lab_test":
                self.score_lab(tool_call)
            
            # TODO: Developing a microbiology scoring metric? 
            # elif action.tool == "request_microbio_test": 
            #     self._score_microbiology(tool_call)
 
        self.scores["Tool Calls"] = output.num_tool_calls
        
        self.answers["Diagnosis"] = output.prediction.final_diagnosis
        self.score_diagnosis()
        self.answers["Treatment"] = output.prediction.treatment
        self.score_treatment()  
        
        return {
            "scores": self.scores,
            "answers": self.answers
        }

    def score_physical_exam(self, idx: int):
        if idx == 0: #physical exam is the first tool called 
            self.scores["Physical Examination"] = 1
            self.scores["Late Physical Examination"] = 1
            self.explanations["Physical"] = "CORRECT: Physical Exam was ordered first."
        else:
            self.scores["Late Physical Examination"] = 1
            if self.scores["Physical Examination"] == 0: 
                self.explanations["Physical"] = "PROTOCOL VIOLATION: Physical Exam was not ordered first."

    #TODO: Check that this works once lab tool is working 
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
                self.answers["Neutral Laboratory Tests"].append(test_id)
            else:
                self.answers["Unnecessary Laboratory Tests"].append(test_id)

    def score_imaging_action(self, tool_call: dict):
        print(tool_call)
        args = tool_call.get("args")
        modality = args.get("modality").lower() 
        region = args.get("region").lower() 
        imaging_dict = {"region": region, "modality": modality}
        
        if not self.score_imaging(region, modality) or imaging_dict in self.answers["Correct Imaging"]:
            self.answers["Unnecessary Imaging"].append(imaging_dict)
        else:
            self.answers["Correct Imaging"].append(imaging_dict)
            
    def score_diagnosis(self):
        print(self.answers["Diagnosis"])
        answer = self.answers["Diagnosis"].lower() 
        for word in answer.split():
            if fuzz.ratio(word, self.pathology) > 90:
                self.scores["Diagnosis"] = 1
                self.scores["Gracious Diagnosis"] = 1
                self.explanations["Diagnosis"] = "CORRECT: Model prediction matches ground truth diagnosis closely."
                print(self.answers["Diagnosis"])
                break
        for alternative_patho in self.alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if patho_loc in answer and patho_mod in answer:
                    self.scores["Diagnosis"] = 1
                    self.scores["Gracious Diagnosis"] = 1
                    self.explanations["Diagnosis"] = "CORRECT: Model prediction matches alternative name for ground truth diagnosis."
                    break
        for alternative_patho in self.gracious_alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if (patho_loc in answer and patho_mod in answer):
                    self.scores["Gracious Diagnosis"] = 1
                    self.explanations["Diagnosis"] = "ACCEPTABLE: Model prediction is similar to the ground truth diagnosis."
                    break
        
        
    
    def print_eval(self, verbose: bool = True, save: bool = True, csv_path: str = ""): 
        done_lab_cat = self.scores["Laboratory Tests"]
        num_required_lab_cat = len(self.required_lab_tests)
        num_neutral_lab = len(self.answers["Neutral Laboratory Tests"])
        num_wrong_lab = len(self.answers["Unnecessary Laboratory Tests"])
        
        done_treat_cat = sum([1 for treat in self.answers["Treatment Requested"].values() if treat])
        num_required_treat_cat = sum([1 for treat in self.answers["Treatment Required"].values() if treat])
        
        if not self.explanations["Physical"]: 
            self.explanations["Physical"] = "PROTOCOL VIOLATION: Physical examination was not ordered"
        if not self.explanations["Diagnosis"]: 
            self.explanations["Diagnosis"] = "INCORRECT: Model does not predict the ground truth diagnosis."
        verbose_eval = f"""
        DIAGNOSIS EVALUATION: 
        {self.explanations["Diagnosis"]}
        PHYSICAL EXAMINATION: 
        {self.explanations["Physical"]}
        IMAGING EVALUATION: 
        {self.explanations["Imaging"]}
        LABORATORY EVALUATION:  
        {done_lab_cat} out of the {num_required_lab_cat} required categories were tested. 
        {num_neutral_lab} neutral labs were ordered. 
        {num_wrong_lab} unnecessary labs were ordered. 
        TREATMENT EVALUATION: 
        {done_treat_cat} out of the {num_required_treat_cat} treatmented were ordered. 
        """ 
        print(self.answers["Diagnosis"])
        evaluation = { 
            "hadm_id": self.hadm_id, 
            "diagnosis": self.answers["Diagnosis"], 
            "gt_diagnosis": self.grounded_diagnosis, 
            "treatment": self.answers["Treatment"], 
            "gt_treatment": self.grounded_treatment, 
            "diagnosis_score": self.scores["Diagnosis"], 
            "gracious_diagnosis_score": self.scores["Gracious Diagnosis"], 
            "tool_calls": self.scores["Tool Calls"], 
            "sat_lab": done_lab_cat / num_required_lab_cat, #proportion of required labs were tested 
            "num_neutral_lab": num_neutral_lab, 
            "num_wrong_lab": num_wrong_lab, 
            "imaging_score": self.scores["Imaging"], 
            "num_wrong_imaging": len(self.answers["Unnecessary Imaging"]), 
            "phys": self.scores["Physical Examination"], 
            "late_phys": self.scores["Late Physical Examination"], 
            "explanation": verbose_eval, 
            "sat_treat": done_treat_cat / num_required_treat_cat #proportion of required treatments that were ordered 
        }
        
        print(verbose_eval)
        if save:
            df = pd.DataFrame([evaluation])
            #Create file if it doesn't exist
            if not os.path.exists(csv_path): 
                df.to_csv(csv_path, index=False)
            else: 
                df.to_csv(csv_path, mode="a", header=False, index=False)
            
    # Subclasses must define these: 
    @abstractmethod
    def score_imaging(self, region: str, modality: str) -> bool:
        pass

    @abstractmethod
    def score_treatment(self):
        pass


