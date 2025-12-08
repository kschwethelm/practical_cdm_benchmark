from cdm.benchmark.data_models import Pathology, GroundTruth
from cdm.evaluators.appendicitis_evaluator import AppendicitisEvaluator
from cdm.evaluators.cholecystitis_evaluator import CholecystitisEvaluator
from cdm.evaluators.diverticulitis_evaluator import DiverticulitisEvaluator
from cdm.evaluators.pancreatitis_evaluator import PancreatitisEvaluator


def get_evaluator(pathology: Pathology, ground_truth: GroundTruth):
    evaluator_map = {
        Pathology.APPENDICITIS: AppendicitisEvaluator,
        Pathology.CHOLECYSTITIS: CholecystitisEvaluator,
        Pathology.DIVERTICULITIS: DiverticulitisEvaluator,
        Pathology.PANCREATITIS: PancreatitisEvaluator,
    }
    evaluator_class = evaluator_map.get(pathology)
    if not evaluator_class:
        raise ValueError(f"No evaluator for pathology: {pathology}")
    return evaluator_class(ground_truth, pathology)
