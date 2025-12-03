from langchain_core.agents import AgentAction
from typing import List, Dict, Tuple, Union
import re
from cdm.benchmark.data_models import AgentRunResult
from thefuzz import fuzz
from abc import abstractmethod

class PathologyEvaluator:

    pathology: str = ""
    alternative_pathology_names: List[Dict] = []
    gracious_alternative_pathology_names: List[Dict] = []
    required_lab_tests: Dict[str, List[str]] = {}
    neutral_lab_tests: List[str] = []

    def __init__(self):
        self._reset_evaluation() 
        
    def _reset_evaluation(self): 
        self.answers = {
            "Diagnosis": "",
            "Treatment": [],
            "Correct Laboratory Tests": {k: [] for k in self.required_lab_tests},
            "Unnecessary Laboratory Tests": [],
            "Correct Imaging": [],
            "Unnecessary Imaging": [],
        }

        self.scores = {
            "Physical Examination": 0,
            "Late Physical Examination": 0,
            "Laboratory Tests": 0,
            "Imaging": 0,
            "Diagnosis": 0,
            "Gracious Diagnosis": 0,
            "Diagnosis Parsing": 0,
            "Treatment Parsing": 0,
            "Tool Calls": 0,
        } 
        
        self.explanations = {
            "Imaging": ""
        }
    def evaluate_case(self, output: AgentRunResult):
        self._reset_evaluation()  
        tool_calls = [m for m in output.messages if "tool_calls" in m]
        tools = [m for m in output.messages if m.get("type") == "tool"]
        assert(len(tool_calls) == len(tools))
        for idx, tool in enumerate(tools):
            tool_name = tool.get("name") #tool_calls is a list of dict
            tool_call = tool_calls[idx]
            if tool_name == "physical_examination":
                self._score_physical_exam(idx)
            elif tool_name == "request_imaging":
                self._score_imaging_action(tool_call)
            elif tool_name == "request_lab_test":
                self._score_lab(tool_call)
            
            # TODO: Developing a microbiology scoring metric? 
            # elif action.tool == "request_microbio_test": 
            #     self._score_microbiology(tool_call)
 
        self.scores["Tool Call"] = output.num_tool_calls()
        
        self.answers["Diagnosis"] = output.prediction.final_diagnosis
        self._score_diagnosis()
        self.answers["Treatment"] = output.prediction.treatment
        self.score_treatment()  

        return {
            "scores": self.scores,
            "answers": self.answers,
        }

    def score_physical_exam(self, idx: int):
        if idx == 0: #physical exam is the first tool called 
            self.scores["Physical Examination"] = 1
            self.scores["Late Physical Examination"] = 1
        else:
            self.scores["Late Physical Examination"] = 1

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
            if test_id not in self.neutral_lab_tests:
                self.answers["Unnecessary Laboratory Tests"].append(test_id)

    def score_imaging_action(self, tool_call: dict):
        args = tool_call.get("args")
        modality = args.get("modality")
        region = args.get("region")
        imaging_dict = {"region": region, "modality": modality}
        
        #TODO: Split into unnecessary and incorrect imaging? 
        if not self.score_imaging(region, modality) or imaging_dict in self.answers["Correct Imaging"]:
            self.answers["Unnecessary Imaging"].append(imaging_dict)
        else:
            self.answers["Correct Imaging"].append(imaging_dict)
            
    #TODO: keyword_positive
    def score_diagnosis(self):
        answer = self.answers["Diagnosis"].lower() 
        for word in answer.split():
            # TODO: maybe consider a different metric? 
            if fuzz.ratio(word, self.pathology) > 90:
                self.scores["Diagnosis"] = 1
                self.scores["Gracious Diagnosis"] = 1
                break
        for alternative_patho in self.alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if patho_loc in answer and patho_mod in answer:
                    self.scores["Diagnosis"] = 1
                    self.scores["Gracious Diagnosis"] = 1
                    break
        for alternative_patho in self.gracious_alternative_pathology_names:
            patho_loc = alternative_patho["location"]
            for patho_mod in alternative_patho["modifiers"]:
                if patho_loc in answer and patho_mod in answer:
                    self.scores["Gracious Diagnosis"] = 1
                    break
    
    # Subclasses must define these: 
    @abstractmethod
    def score_imaging(self, region: str, modality: str) -> bool:
        pass

    @abstractmethod
    def score_treatment(self):
        pass
