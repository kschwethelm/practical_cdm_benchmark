import csv
import json
from collections import defaultdict
from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cdm.evaluators.utils import calculate_average, count_treatment, count_unnecessary

PATHOLOGIES = ["appendicitis", "cholecystitis", "diverticulitis", "pancreatitis"]

MODALITY_ORDER = ["CT", "Ultrasound", "MRI", "Radiograph", "Other", "None"]

MODEL_COLOUR = {
    "Llama3.3-70B": "#0077B6",
    "OASST-70B": "#00B4D8",
    "WizardLM-70B": "#90E0EF",
    "Mistral-24B": "#F97F77",
    "Qwen3-30B": "#4c956c",
    "GPTOSS-20B": "#8d5dbd",
    "Mean": "#e56b6f",
}

MODALITY_COLOUR = {
    "CT": "#C2C2C2",
    "Ultrasound": "#8A817C",
    "MRI": "#58534B",
    "Radiograph": "#4F5B62",
    "Other": "#FE6D73",
    "None": "#D6CCC2",
}

CORRECT_MODALITY_COLOUR = "#4CAF50"

PREFERRED_MODALITIES = {
    "Appendicitis": {"Ultrasound"},
    "Pancreatitis": {"Ultrasound"},
    "Diverticulitis": {"CT"},
    "Cholecystitis": {"Ultrasound"},
}

IMAGING_MODALITY_MAP = {
    "ct": "CT",
    "ctu": "CT",
    "mri": "MRI",
    "mra": "MRI",
    "mrcp": "MRI",
    "mre": "MRI",
    "ultrasound": "Ultrasound",
    "eus": "Ultrasound",
    "carotid ultrasound": "Ultrasound",
    "radiograph": "Radiograph",
    "ercp": "Radiograph",
    "upper gi series": "Radiograph",
    "hida": "Other",
    "ptc": "Other",
    "drainage": "Other",
}


def read_jsonl(path: str) -> Iterable[dict]:
    """
    Convert jsonl file to Iterable dict.

    :param path: jsonl file path
    :type path: str
    :return: iterable dict object
    :rtype: Iterable[dict]
    """
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def aggregate_jsonl(results_path: str) -> tuple[dict[str, list], list]:
    """
    Reads a jsonl results file for a specific model and groups results by pathology

    :param results_path: Path to jsonl file
    :type results_path: str
    :return: Results grouped by pathology, list of scoring fields in the file
    :rtype: tuple[dict[str, list], list]
    """
    results = {"appendicitis": [], "cholecystitis": [], "diverticulitis": [], "pancreatitis": []}
    fields = []

    for obj in read_jsonl(results_path):
        if not fields:
            fields = list(obj.get("scores").keys())
            if "answers" in obj:
                fields += [
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
        results, fields = aggregate_jsonl(results_path=result_path)
        for field in fields:
            for pathology in ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]:
                if pathology in results.keys():
                    if field in ["Unnecessary Imaging"]:
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

        bars = plt.bar(offsets, values, width=width, label=model)

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
        for obj in read_jsonl(path):
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


def plot_treatment_requests(model_paths: dict, save_path: str | None = None):
    """
    Plot a grid with the 4 different pathologies and each required treatment.

    :param model_paths: dictionary of models and the paths to their result files
    :type dict
    :param save_path: path to save plot to
    :type save_path: str | None
    """
    df = extract_treatment_request_df(model_paths)
    df_agg = aggregate_treatment_requests(df)
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
                offsets, values, width=width, label=model, color=MODEL_COLOUR.get(model, "#999999")
            )

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


def aggregate_lab_requests(model_paths: dict) -> dict:
    """
    Calculates percentage of required labs requested per pathology and model.

    :param model_paths: dictionary of models and the paths to their result files
    :type model_paths: dict
    :return: Dictionary of calculated percentages
    :rtype: dict
    """
    counts = defaultdict(lambda: defaultdict(int))
    hits = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for model, path in model_paths.items():
        for obj in read_jsonl(path):
            pathology = obj["pathology"]
            answers = obj.get("answers", {})
            correct_labs = answers.get("Correct Laboratory Tests", {})

            counts[model][pathology] += 1

            for category, requested in correct_labs.items():
                if requested:
                    hits[model][pathology][category] += 1

    percentages = defaultdict(lambda: defaultdict(dict))
    for model in hits:
        for pathology in hits[model]:
            n = counts[model][pathology]
            for category, c in hits[model][pathology].items():
                percentages[model][pathology][category] = (c / n) * 100 if n > 0 else np.nan
    return percentages


def plot_lab_requests(model_paths: dict, save_path: str | None = None):
    """
    Plot a grid with the 4 different pathologies and each required lab category.

    :param model_paths: dictionary of models and the paths to their result files
    :type model_paths: dict
    :param save_path: path to save plot to
    :type save_path: str | None
    """
    data = aggregate_lab_requests(model_paths)
    print(data)
    models = list(data.keys())
    pathologies = ["appendicitis", "cholecystitis", "pancreatitis", "diverticulitis"]

    fig, axes = plt.subplots(2, 2, figsize=(18, 12), sharey=True)
    axes = axes.flatten()

    for ax, pathology in zip(axes, pathologies, strict=False):
        categories = sorted({cat for model in data for cat in data[model].get(pathology, {})})
        x = np.arange(len(categories))
        width = 0.8 / len(models)
        for i, model in enumerate(models):
            values = [data[model].get(pathology, {}).get(cat, np.nan) for cat in categories]

            offsets = x + (i - (len(models) - 1) / 2) * width

            bars = ax.bar(
                offsets, values, width=width, label=model, color=MODEL_COLOUR.get(model, "#999999")
            )

            for bar, val in zip(bars, values, strict=False):
                if np.isnan(val):
                    continue
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"{val:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                )

        ax.set_title(pathology.capitalize(), fontsize=15)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=13)
        ax.set_ylabel("Lab Test Requested (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle="--", alpha=0.6)

        for j in range(len(categories) - 1):
            ax.axvline(j + 0.5, color="gray", linestyle="--", linewidth=1)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.05),
        ncol=len(models),
        frameon=False,
    )

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def aggregate_imaging_requests(model_paths: dict) -> pd.DataFrame:
    """
    Aggregate imaging requests per model and pathology.

    :param model_paths: dictionary of models and the paths to their result files
    :type model_paths: dict
    :return: dataframe with coloums model, pathology, modality
    :rtype: DataFrame
    """
    rows = []
    for model, path in model_paths.items():
        for obj in read_jsonl(path):
            pathology = obj["pathology"]
            answers = obj.get("answers", {})

            imaging_list = answers.get("Correct Imaging", [])
            modality = "None"

            for img in imaging_list:
                if img.get("region", "").lower() == "abdomen":
                    modality = img.get("modality", "").lower()
                    modality = IMAGING_MODALITY_MAP.get(modality, "Other")
                    break

            rows.append({"Model": model, "Pathology": pathology.capitalize(), "Modality": modality})

    df = pd.DataFrame(rows)

    counts = df.groupby(["Model", "Pathology", "Modality"]).size().reset_index(name="Counts")
    totals = counts.groupby(["Model", "Pathology"])["Counts"].transform("sum")
    counts["Percentage"] = counts["Counts"] / totals * 100
    return counts


def plot_imaging_requests(model_paths: dict, save_path: str | None = None):
    """
    Plot stacked bar charts of imaging modality requests by pathology and model.

    :param model_paths: dictionary of models and the paths to their result files
    :type model_paths: dict
    :param save_path: path to save plot to
    :type save_path: str | None
    """

    df = aggregate_imaging_requests(model_paths)

    models = list(df["Model"].unique())
    pathologies = ["Appendicitis", "Cholecystitis", "Diverticulitis", "Pancreatitis"]
    model_hatches = {
        model: hatch
        for model, hatch in zip(models, ["", "//", "xx", "..", "++", "oo"], strict=False)
    }
    n_models = len(models)
    bar_width = 0.18
    x = np.arange(len(pathologies))

    plt.figure(figsize=(14, 6))

    for i, model in enumerate(models):
        offsets = x + (i - (n_models - 1) / 2) * bar_width
        bottom = np.zeros(len(pathologies))

        for modality in MODALITY_ORDER:
            vals = (
                df[(df["Model"] == model) & (df["Modality"] == modality)]
                .set_index("Pathology")
                .reindex(pathologies)["Percentage"]
                .fillna(0)
                .values
            )

            bar_colors = []

            for pathology in pathologies:
                is_preferred = (
                    pathology in PREFERRED_MODALITIES
                    and modality in PREFERRED_MODALITIES[pathology]
                )
                bar_colors.append(
                    CORRECT_MODALITY_COLOUR if is_preferred else MODALITY_COLOUR[modality]
                )

            bars = plt.bar(
                offsets,
                vals,
                width=bar_width,
                bottom=bottom,
                color=bar_colors,
                edgecolor="black",
                hatch=model_hatches[model],
                label=modality if i == 0 else "",
            )

            for bar, v in zip(bars, vals, strict=False):
                if v >= 5:
                    plt.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + v / 2,
                        f"{v:.0f}",
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="white" if modality in {"MRI", "Radiograph"} else "black",
                        weight="bold",
                    )

            bottom += vals

    plt.xticks(x, pathologies)
    plt.ylabel("Imaging Modality Requested (%)")
    plt.ylim(0, 100)  # percentages must add up to 100

    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles, strict=False))
    from matplotlib.patches import Patch

    model_legend = [
        Patch(facecolor="white", edgecolor="black", hatch=model_hatches[m], label=m) for m in models
    ]

    plt.legend(
        handles=list(by_label.values()) + model_legend,
        labels=list(by_label.keys()) + models,
        bbox_to_anchor=(0.95, 1.25),
        ncol=3,
        frameon=False,
        fontsize=12,
    )

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    model_paths = {}

    model_paths["tool_calling"] = {
        "Qwen3-30B": "outputs/presentation3/results_qwen3_30b_nothinking_cdm.jsonl",
        "Mistral-24B": "outputs/presentation3/results_mistral_24b_cdm.jsonl",
        "GPTOSS-20B": "outputs/presentation3/results_gptoss_cdm.jsonl",
    }
    model_paths["rag_tool_calling"] = {
        "Qwen3-30B": "outputs/presentation3/results_qwen3_30b_thinking_rag_cdm.jsonl",
        "Mistral-24B": "outputs/presentation3/results_mistral_24b_rag_cdm.jsonl",
        "GPTOSS-20B": "outputs/presentation3/results_gptoss_rag_cdm.jsonl",
    }

    model_paths["full_info"] = {
        "Qwen3-30B": "outputs/results_qwen3_30b_full_info.jsonl",
        "DeepSeek-R1-Distill-Llama-70B": "outputs/results_deepseekr1_70b_full_info.jsonl",
        "MedGemma-27B": "outputs/results_medgemma_27b_full_info.jsonl",
    }

    tool_call_averages, tool_call_n = aggregate_results(model_paths["tool_calling"])
    rag_tool_call_averages, rag_tool_call_n = aggregate_results(model_paths["rag_tool_calling"])
    full_info_averages, full_info_n = aggregate_results(model_paths["full_info"])

    x_labels = [p.capitalize() for p in PATHOLOGIES] + ["Mean"]
    plot_grouped_bar_chart(
        data=full_info_averages["Diagnosis"],
        title="Diagnostic Accuracy (%) by Pathology - Full Info",
        ylabel="Diagnostic Accuracy (%)",
        groups=PATHOLOGIES,
        x_labels=x_labels,
        save_path="outputs/presentation3/diagnosis_full_info_pres3_accuracy.png",
    )

    phys = ["Physical Examination", "Late Physical Examination"]
    phys_x_labels = [p.capitalize() for p in phys]
    phys_data = aggregate_phys(tool_call_averages)
    plot_grouped_bar_chart(
        data=phys_data,
        ylabel="Diagnostic Accuracy (%)",
        groups=phys,
        x_labels=phys_x_labels,
        save_path="outputs/presentation3/physical_examination.png",
    )

    plot_imaging_requests(
        model_paths["rag_tool_calling"], save_path="outputs/presentation3/imaging_requests.png"
    )

    plot_lab_requests(
        model_paths["rag_tool_calling"], save_path="outputs/presentation3/lab_requests.png"
    )
