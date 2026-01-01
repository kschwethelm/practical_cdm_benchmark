import csv
import json
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

from cdm.evaluators.utils import calculate_average, count_treatment, count_unnecessary


def read_jsonl(results_path: str) -> tuple[dict[str, list], list]:
    """
    Reads a jsonl results file for a specific model and groups results by pathology

    :param results_path: Path to jsonl file
    :type results_path: str
    :return: Results group by pathology, list of scoring fields in the file
    :rtype: tuple[dict[str, list], list]
    """
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


def plot_graphs(model_paths: dict) -> tuple[dict, dict, dict]:
    """
    Compute average scores, sample counts, and percentages for given models.

    :param model_paths: Mapping of model names to their jsonl results files.
    :type model_paths: dict
    :return: Average scores per field, model and pathology; Sample counts per field, model, and pathology;
        Percentage scores per field, model, and pathology
    :rtype: Tuple[dict, dict, dict]
    """
    avg_scores = defaultdict(lambda: defaultdict(dict))
    avg_samples = defaultdict(lambda: defaultdict(dict))
    percentages = defaultdict(lambda: defaultdict(dict))

    for model_name, result_path in model_paths.items():
        results, fields = read_jsonl(results_path=result_path)
        for field in fields:
            for pathology in ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]:
                if pathology in results.keys():
                    if field in ["Unnecessary Laboratory Tests", "Unnecessary Imaging"]:
                        results[pathology] = count_unnecessary(results[pathology], field)
                    if field == "Treatment Requested":
                        results[pathology] = count_treatment(results[pathology])
                    avg, n = calculate_average(results[pathology], field)
                    avg_scores[field][model_name][pathology] = avg
                    avg_samples[field][model_name][pathology] = n
                    if field == "Diagnosis":
                        percentages[field][model_name][pathology] = avg * 100
                    if field == "Treatment Requested":
                        percentages[field][model_name][pathology] = avg * 100
    return avg_scores, avg_samples, percentages


def plot_grouped_bar_chart(
    data: dict, title: str, ylabel: str, save_path: str | None = None
) -> None:
    """
    Plot a grouped bar chart showing model performance per pathology

    :param data: Data to plot per field, model and pathology
    :type data: dict
    :param title: Title of chart
    :type title: str
    :param ylabel: Label of y-axis
    :type ylabel: str
    :param save_path: Path to save chart to.
    :type save_path: str | None
    """
    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]
    x_labels = [p.capitalize() for p in pathologies] + ["Mean"]
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
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=200)
    plt.show()


def write_stats_to_csv(avg_samples: dict, output_path: str) -> None:
    """
    Save the breakdown of sample counts per pathology and model.

    :param avg_samples: Sample counts per field, model and pathology.
    :type avg_samples: dict
    :param output_path: Path to output csv file.
    :type output_path: str
    """
    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]
    model_counts = {}
    for _, models in avg_samples.items():
        for model, pathology_counts in models.items():
            if model not in model_counts:
                model_counts[model] = {p: 0 for p in pathologies}

            for p in pathologies:
                model_counts[model][p] += pathology_counts.get(p, 0)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Model"] + [p.capitalize() for p in pathologies] + ["Total"])

        for model, pathology_counts in models.items():
            counts = [pathology_counts.get(p, 0) for p in pathologies]
            total_n = sum(counts)

            writer.writerow([model] + counts + [total_n])


if __name__ == "__main__":
    model_paths = {}
    model_paths["cdm"] = {
        "Qwen3-30B": "outputs/results_qwen3_30b_cdm.jsonl",
        "LLama3.3-70B": "outputs/results_llama3_70b_cdm.jsonl",
    }
    model_paths["full_info"] = {
        "OASST-70B": "outputs/results_oasst_70b_full_info.jsonl",
        "WizardLM-70B": "outputs/results_wizardlm_70b_full_info.jsonl",
        "OpenBioLLM-70B": "outputs/results_openbio_70b_full_info.jsonl",
        "LLama3.3-70B": "outputs/results_llama3_70b_full_info.jsonl",
        "ClinicalCamel-70B": "outputs/results_clinical_camel_70b_full_info.jsonl",
    }
    model_paths["new"] = {
        "Qwen3-30B": "outputs/results_qwen3_30b_full_info.jsonl",
        "DeepSeek-R1-Distill-Llama-70B": "outputs/results_deepseekr1_70b_full_info.jsonl",
        "DeepSeek-R1-Distill-Qwen-14B": "outputs/results_deepseekr1_14b_full_info.jsonl",
    }

    _, _, cdm_percentages = plot_graphs(model_paths["cdm"])
    _, sample_count, full_info_percentages = plot_graphs(model_paths["full_info"])
    _, _, new_model_percentages = plot_graphs(model_paths["new"])

    plot_grouped_bar_chart(
        data=cdm_percentages["Diagnosis"],
        title="Diagnostic Accuracy (%) by Pathology",
        ylabel="Accuracy (%)",
        save_path="outputs/diagnosis_accuracy.png",
    )

    plot_grouped_bar_chart(
        data=full_info_percentages["Diagnosis"],
        title="Diagnostic Accuracy (%) by Pathology",
        ylabel="Accuracy (%)",
        save_path="outputs/diagnosis_full_info_accuracy.png",
    )

    plot_grouped_bar_chart(
        data=new_model_percentages["Diagnosis"],
        title="Diagnostic Accuracy (%) by Pathology",
        ylabel="Accuracy (%)",
        save_path="outputs/diagnosis_full_info_new_accuracy.png",
    )
    write_stats_to_csv(sample_count, "outputs/full_info_sample_count.csv")
