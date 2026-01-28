import csv
import json
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cdm.evaluators.utils import calculate_average, count_treatment, count_unnecessary

color_map = {
    "Llama3.3-70B": "#0077B6",
    "OASST-70B": "#00B4D8",
    "WizardLM-70B": "#90E0EF",
    "Mistral-24B": "#F97F77",
    "Qwen3-30B": "#4c956c",
    "GPTOSS-20B": "#8d5dbd",
    "Mean": "#e56b6f",
}


def read_jsonl(results_path: str) -> tuple[dict[str, list], list]:
    """
    Reads a jsonl results file for a specific model and groups results by pathology

    :param results_path: Path to jsonl file
    :type results_path: str
    :return: Results grouped by pathology, list of scoring fields in the file
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


def aggregate_results(model_paths: dict) -> tuple[dict, dict, dict]:
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

    return avg_scores, avg_samples


def aggregate_phys(data: dict) -> dict:
    """
    Averages the physical examination scores across pathologies for each model.

    :param data: average scores
    :type data: dict
    :return: dict with only the averaged physical examination scores.
    :rtype: dict
    """
    phys_dict = defaultdict(dict)
    for field, models in data.items():
        if field not in ["Physical Examination", "Late Physical Examination"]:
            continue
        for model, pathology_vals in models.items():
            values = [v for v in pathology_vals.values() if v is not None and not np.isnan(v)]
            phys_dict[model][field] = float(np.mean(values)) if values else np.nan
    return phys_dict


def plot_grouped_bar_chart(
    data: dict,
    ylabel: str,
    groups: list,
    x_labels: list,
    title: str | None = None,
    save_path: str | None = None,
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

    models = list(data.keys())
    n_models = len(models)
    x = np.arange(len(x_labels))
    width = 0.8 / n_models

    plt.figure(figsize=(10, 5))

    for i, model in enumerate(models):
        values = [data[model].get(p, np.nan) * 100 for p in groups]
        if "Mean" in x_labels:
            mean = np.nanmean(values)
            values.append(mean)
        offsets = x + (i - (n_models - 1) / 2) * width

        bars = plt.bar(
            offsets, values, width=width, label=model, color=color_map.get(model, "#999999")
        )

        for bar, val in zip(bars, values, strict=False):
            if np.isnan(val):
                continue
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.xticks(x, x_labels, rotation=25, ha="right")
    plt.ylabel(ylabel)
    if title:
        plt.title(title)
    plt.ylim(0, 100)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=len(models), frameon=False)
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


def extract_treatment_request_df(model_paths: dict) -> tuple[pd.DataFrame, dict]:
    """
    Extracts the requested treatment counts; if case is correctly diagnosed by model then add to dataframe.

    :param model_paths: dictionary of models and the paths to their result files
    :type model_paths: dict
    :return: [Model, Pathology, Treatment, Requested]
    :rtype: tuple[DataFrame, dict]
    """
    rows = []
    treatment_required_counts = defaultdict(lambda: defaultdict(int))

    for model, path in model_paths.items():
        with open(path) as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                pathology = obj["pathology"]
                answers = obj.get("answers", {})
                scores = obj.get("scores", {})

                treatment_required = answers.get("Treatment Required", {})
                treatment_requested = answers.get("Treatment Requested", {})
                correctly_diagnosed = scores.get("Diagnosis", False)

                for treatment, required in treatment_required.items():
                    # if treatment is not required then don't count it even if requested
                    if not required:
                        continue

                    treatment_required_counts[pathology][treatment] += 1
                    # if treatment is required and case is correctly diagnosed then add to df
                    if correctly_diagnosed:
                        requested = treatment_requested.get(treatment, False)
                        rows.append([model, pathology, treatment, requested])

    df = pd.DataFrame(rows, columns=["Model", "Pathology", "Treatment", "Requested"])
    return df


def aggregate_treatment_requests(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates percentage of treatments requested per required treatment and pathology

    :param df: dataframe with the treatment requested counts
    :type df: pd.DataFrame
    :return: dataframe with aggregated data
    :rtype: DataFrame
    """
    df_agg = df.groupby(["Model", "Pathology", "Treatment"]).mean().reset_index()
    df_agg["Request Correct"] = df_agg["Requested"] * 100
    df_counts = df.groupby(["Pathology", "Treatment", "Model"]).size().reset_index(name="Counts")

    return df_agg.merge(df_counts, on=["Pathology", "Treatment", "Model"], how="left")


def plot_treatment_request_grid_matplotlib(df_agg: pd.DataFrame, save_path: str | None = None):
    """
    Plot a grid with the 4 different pathologies and each required treatment.

    :param df_agg: dataframe with aggregated data
    :type df_agg: pd.DataFrame
    :param save_path: path to save plot to
    :type save_path: str | None
    """
    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]
    models = sorted(df_agg["Model"].unique())

    fig, axes = plt.subplots(2, 2, figsize=(20, 12), sharey=True)
    axes = axes.flatten()

    for ax, pathology in zip(axes, pathologies, strict=False):
        df_p = df_agg[df_agg["Pathology"] == pathology]

        treatments = list(df_p["Treatment"].unique())
        n_treatments = len(treatments)
        n_models = len(models)

        x = np.arange(n_treatments)
        width = 0.8 / n_models

        for i, model in enumerate(models):
            df_m = df_p[df_p["Model"] == model]

            values = [
                df_m[df_m["Treatment"] == t]["Request Correct"].values[0]
                if t in df_m["Treatment"].values
                else np.nan
                for t in treatments
            ]

            offsets = x + (i - (n_models - 1) / 2) * width

            bars = ax.bar(
                offsets, values, width=width, label=model, color=color_map.get(model, "#999999")
            )

            # Annotate bars
            for bar, val in zip(bars, values, strict=False):
                if np.isnan(val):
                    continue
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 2,
                    f"{val:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=12,
                )

        # Vertical separators
        for j in range(n_treatments - 1):
            ax.axvline(j + 0.5, color="gray", linestyle="--", linewidth=1)

        ax.set_xticks(x)
        ax.set_xticklabels(treatments, fontsize=14)
        ax.set_title(f"{pathology.capitalize()} Treatment", fontsize=16)
        ax.set_ylabel("Treatment Requested (%)")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle="--", alpha=0.6)

    for ax in axes[len(pathologies) :]:
        ax.axis("off")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=len(models),
        frameon=False,
        fontsize=14,
    )

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    model_paths = {}

    model_paths["tool_calling"] = {
        "Qwen3-30B": "outputs/presentation3/results_qwen3_30b_thinking_cdm.jsonl",
        "Mistral-24B": "outputs/presentation3/results_mistral_24b_cdm.jsonl",
        "GPTOSS-20B": "outputs/presentation3/results_gptoss_cdm.jsonl",
    }
    model_paths["rag_tool_calling"] = {
        "Qwen3-30B": "outputs/presentation3/results_qwen3_30b_thinking_rag_cdm.jsonl",
        "Mistral-24B": "outputs/presentation3/results_mistral_24b_rag_cdm.jsonl",
        "GPTOSS-20B": "outputs/presentation3/results_gptoss_rag_cdm.jsonl",
    }

    model_paths["full_info"] = {
        "Llama3.3-70B": "outputs/results_llama3_70b_full_info.jsonl",
        "OASST-70B": "outputs/results_oasst_70b_full_info.jsonl",
        "WizardLM-70B": "outputs/results_wizardlm_70b_full_info.jsonl",
    }

    tool_call_averages, tool_call_n = aggregate_results(model_paths["tool_calling"])
    rag_tool_call_averages, rag_tool_call_n = aggregate_results(model_paths["rag_tool_calling"])

    df = extract_treatment_request_df(model_paths["rag_tool_calling"])
    df_agg = aggregate_treatment_requests(df)

    plot_treatment_request_grid_matplotlib(
        df_agg,
        save_path="outputs/presentation3/treatment_requested_tool_calling_rag.png",
    )

    phys = ["Physical Examination", "Late Physical Examination"]
    phys_x_labels = [p.capitalize() for p in phys]
    phys_data = aggregate_phys(tool_call_averages)
    plot_grouped_bar_chart(
        data=phys_data,
        title="Whatever",
        ylabel="Diagnostic Accuracy (%)",
        groups=phys,
        x_labels=phys_x_labels,
        save_path="outputs/presentation3/physical_examination.png",
    )

    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]
    x_labels = [p.capitalize() for p in pathologies] + ["Mean"]
    plot_grouped_bar_chart(
        data=tool_call_averages["Diagnosis"],
        title="Diagnostic Accuracy for Agentic Models",
        ylabel="Diagnostic Accuracy (%)",
        groups=pathologies,
        x_labels=x_labels,
        save_path="outputs/presentation3/diagnosis_tool_calling_pres3_accuracy.png",
    )

    plot_grouped_bar_chart(
        data=rag_tool_call_averages["Diagnosis"],
        title="Diagnostic Accuracy for Agentic Models + RAG",
        ylabel="Diagnostic Accuracy (%)",
        groups=pathologies,
        x_labels=x_labels,
        save_path="outputs/presentation3/diagnosis_rag_tool_calling_pres3_accuracy.png",
    )
