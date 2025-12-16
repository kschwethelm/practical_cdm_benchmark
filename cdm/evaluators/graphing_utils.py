import json
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

from cdm.evaluators.utils import calculate_avergae, count_treatment, count_unnecessary


# Get scores from the jsonl results file for a specific model per pathology
def read_jsonl(results_path: str) -> tuple[dict[list], list]:
    results = {"appendicitis": [], "cholecystitis": [], "diverticulitis": [], "pancreatitis": []}
    fields = []
    with open(results_path) as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                if not fields:
                    fields = list(obj.get("scores").keys())
                    if "answers" in obj:
                        fields += [
                            "Unnecessary Laboratory Tests",
                            "Unnecessary Imaging",
                            "Treatment Requested",
                        ]
                if obj.get("pathology") in results.keys():
                    results[obj.get("pathology")].append(obj)
    return results, fields


def plot_graphs(run_type: str = "cdm"):
    avg_scores = defaultdict(lambda: defaultdict(dict))
    avg_samples = defaultdict(lambda: defaultdict(dict))
    percentages = defaultdict(lambda: defaultdict(dict))
    if run_type == "cdm":
        model_paths = {
            "qwen3-4B": "outputs/results_qwen3_4b_cdm.jsonl",
        }
    elif run_type == "full_info":
        model_paths = {
            "Qwen3-4B": "outputs/results_qwen3_4b_full_info.jsonl",
            "OpenBio-8B": "outputs/results_openbio_8b_full_info.jsonl",
            "MedGemma-4B": "outputs/results_medgemma_4b_full_info.jsonl",
            "DeppSeek-14B": "outputs/results_deepseekr1_14b_full_info.jsonl",
            "OASST-70B": "outputs/results_oasst_70b_full_info.jsonl",
            "WizardLM-70B": "outputs/results_wizardlm_70b_full_info.jsonl",
            "MedGemma-27B": "outputs/results_medgemma_27b_full_info.jsonl",
            "DeepSeek-70B": "outputs/results_deepseekr1_70b_full_info.jsonl",
        }
    for model_name, result_path in model_paths.items():
        results, fields = read_jsonl(results_path=result_path)
        for field in fields:
            for pathology in ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]:
                if pathology in results.keys():
                    if field in ["Unnecessary Laboratory Tests", "Unnecessary Imaging"]:
                        results[pathology] = count_unnecessary(results[pathology], field)
                    if field == "Treatment Requested":
                        results[pathology] = count_treatment(results[pathology])
                    avg, n = calculate_avergae(results[pathology], field)
                    avg_scores[field][model_name][pathology] = avg
                    avg_samples[field][model_name][pathology] = n
                    if field == "Diagnosis":
                        percentages[field][model_name][pathology] = avg * 100
                    if field == "Treatment Requested":
                        percentages[field][model_name][pathology] = avg * 100
    return avg_scores, avg_samples, percentages


def plot_grouped_bar_chart(data: dict, title: str, ylabel: str, save_path: str | None = None):
    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]
    x_labels = pathologies + ["Mean"]
    models = list(data.keys())
    n_models = len(models)
    x = np.arange(len(x_labels))
    width = 0.8 / n_models

    plt.figure(figsize=(10, 5))

    for i, model in enumerate(models):
        values = [data[model].get(p, np.nan) for p in pathologies]
        mean = np.nanmean(values)
        values.append(mean)
        offsets = x + (i - (n_models - 1) / 2) * width
        plt.bar(offsets, values, width=width, label=model)

    plt.xticks(x, x_labels, rotation=25, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.ylim(0, 100)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=200)
    plt.show()


if __name__ == "__main__":
    # _, _, cdm_percentages = plot_graphs()
    _, _, full_info_percentages = plot_graphs(run_type="full_info")

    # plot_grouped_bar_chart(
    #     data=cdm_percentages["Diagnosis"],
    #     title="Diagnostic Accuracy (%) by Pathology",
    #     ylabel="Accuracy (%)",
    #     save_path="outputs/diagnosis_accuracy.png"
    # )

    plot_grouped_bar_chart(
        data=full_info_percentages["Diagnosis"],
        title="Diagnostic Accuracy (%) by Pathology",
        ylabel="Accuracy (%)",
        save_path="outputs/diagnosis_full_info_accuracy.png",
    )

    # plot_grouped_bar_chart(
    #     data=cdm_percentages["Treatment Requested"],
    #     title="Treatment Request Accuracy (%) by Pathology",
    #     ylabel="Accuracy (%)",
    #     save_path="outputs/treatment_requested.png"
    # )
