"""Streamlit UI for comparing benchmark cases from two different JSON files."""

import difflib
import json
from pathlib import Path

import streamlit as st
from loguru import logger

from cdm.benchmark.data_models import BenchmarkDataset, HadmCase

# Color palettes for highlighting matching blocks
# Light mode - pastel colors
HIGHLIGHT_COLORS_LIGHT = [
    "#FFE6E6",  # Light red
    "#E6F3FF",  # Light blue
    "#E6FFE6",  # Light green
    "#FFF5E6",  # Light orange
    "#F0E6FF",  # Light purple
    "#FFFFE6",  # Light yellow
    "#FFE6F5",  # Light pink
    "#E6FFFF",  # Light cyan
]

# Dark mode - darker, more saturated colors
HIGHLIGHT_COLORS_DARK = [
    "#4A2020",  # Dark red
    "#1A3A4A",  # Dark blue
    "#204A20",  # Dark green
    "#4A3A1A",  # Dark orange
    "#3A2A4A",  # Dark purple
    "#4A4A1A",  # Dark yellow
    "#4A2A3A",  # Dark pink
    "#1A4A4A",  # Dark cyan
]

# CSS color variables that will be assigned dynamically
COLOR_VARS = [f"--highlight-color-{i}" for i in range(8)]


def find_matching_blocks(
    text1: str, text2: str, min_length: int = 20
) -> list[tuple[int, int, int]]:
    """
    Find matching text blocks between two strings, ignoring linebreaks.

    Args:
        text1: First text string
        text2: Second text string
        min_length: Minimum length of matching blocks to consider

    Returns:
        List of (i, j, n) tuples where text1[i:i+n] == text2[j:j+n]
    """
    if not text1 or not text2:
        return []

    # Normalize texts by replacing linebreaks with spaces for comparison
    normalized_text1 = text1.replace("\n", " ")
    normalized_text2 = text2.replace("\n", " ")

    matcher = difflib.SequenceMatcher(None, normalized_text1, normalized_text2)
    blocks = []

    for i, j, n in matcher.get_matching_blocks():
        if n >= min_length:
            blocks.append((i, j, n))

    return blocks


def highlight_text(text: str, highlights: list[tuple[int, int, str]]) -> str:
    """
    Apply HTML highlighting to text based on highlight ranges.

    Args:
        text: Text to highlight
        highlights: List of (start, end, color) tuples

    Returns:
        HTML string with highlighted text
    """
    if not text or not highlights:
        return text.replace("\n", "<br>")

    # Sort highlights by start position
    highlights = sorted(highlights, key=lambda x: x[0])

    result = []
    last_pos = 0

    for start, end, color in highlights:
        # Add unhighlighted text before this highlight
        if start > last_pos:
            result.append(text[last_pos:start].replace("\n", "<br>"))

        # Add highlighted text
        highlighted_text = text[start:end].replace("\n", "<br>")
        result.append(f'<span style="background-color: {color};">{highlighted_text}</span>')

        last_pos = end

    # Add remaining unhighlighted text
    if last_pos < len(text):
        result.append(text[last_pos:].replace("\n", "<br>"))

    return "".join(result)


def merge_highlights(highlights: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """
    Merge overlapping highlight ranges, preferring the first color.

    Args:
        highlights: List of (start, end, color) tuples

    Returns:
        Merged list of non-overlapping highlights
    """
    if not highlights:
        return []

    # Sort by start position
    highlights = sorted(highlights, key=lambda x: x[0])

    merged = [highlights[0]]

    for start, end, color in highlights[1:]:
        last_start, last_end, last_color = merged[-1]

        if start <= last_end:
            # Overlapping - extend the range
            merged[-1] = (last_start, max(end, last_end), last_color)
        else:
            # Non-overlapping - add new highlight
            merged.append((start, end, color))

    return merged


def create_highlighted_pair(text1: str, text2: str, min_match_length: int = 20) -> tuple[str, str]:
    """
    Create color-highlighted versions of two texts showing their matches.

    Args:
        text1: First text
        text2: Second text
        min_match_length: Minimum length of matching blocks to highlight

    Returns:
        Tuple of (highlighted_text1, highlighted_text2)
    """
    if not text1:
        text1 = ""
    if not text2:
        text2 = ""

    # Find matching blocks between the two texts
    matches = find_matching_blocks(text1, text2, min_match_length)

    # Create highlight lists for both texts
    highlights_1: list[tuple[int, int, str]] = []
    highlights_2: list[tuple[int, int, str]] = []

    color_idx = 0

    # Add highlights for matches
    for i, j, n in matches:
        # Use CSS variable that will adapt to light/dark mode
        color = f"var(--highlight-color-{color_idx % len(COLOR_VARS)})"
        highlights_1.append((i, i + n, color))
        highlights_2.append((j, j + n, color))
        color_idx += 1

    # Merge overlapping highlights and apply
    highlighted_1 = highlight_text(text1, merge_highlights(highlights_1))
    highlighted_2 = highlight_text(text2, merge_highlights(highlights_2))

    return highlighted_1, highlighted_2


def generate_color_scheme_css() -> str:
    """
    Generate CSS with color variables that adapt to light/dark mode.

    Returns:
        CSS string with media queries for light and dark modes
    """
    # Light mode color definitions
    light_mode_vars = "\n".join(
        [f"    --highlight-color-{i}: {color};" for i, color in enumerate(HIGHLIGHT_COLORS_LIGHT)]
    )

    # Dark mode color definitions
    dark_mode_vars = "\n".join(
        [f"    --highlight-color-{i}: {color};" for i, color in enumerate(HIGHLIGHT_COLORS_DARK)]
    )

    css = f"""
    <style>
    /* Light mode colors (default) */
    :root {{
{light_mode_vars}
    }}

    /* Dark mode colors */
    @media (prefers-color-scheme: dark) {{
        :root {{
{dark_mode_vars}
        }}
    }}

    .text-box {{
        height: 400px;
        overflow-y: auto;
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 5px;
        background-color: #f9f9f9;
        font-family: monospace;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
    }}

    /* Dark mode text box styling */
    @media (prefers-color-scheme: dark) {{
        .text-box {{
            background-color: #1e1e1e;
            border-color: #444;
            color: #e0e0e0;
        }}
    }}
    </style>
    """
    return css


def load_benchmark_dataset(file_path: str) -> BenchmarkDataset:
    """Load benchmark dataset from JSON file using Pydantic model."""
    with open(file_path) as f:
        data = json.load(f)
    return BenchmarkDataset(**data)


def render_demographics(case: HadmCase, label: str):
    """Render demographics section."""
    st.markdown(f"**{label}**")
    if case.demographics:
        st.write(f"Age: {case.demographics.age}, Gender: {case.demographics.gender}")
    else:
        st.warning("No demographics data")


def render_pathology(case: HadmCase, label: str):
    """Render pathology section."""
    st.markdown(f"**{label}**")
    if case.pathology:
        st.write(f"Pathology: {case.pathology.value}")
    else:
        st.info("No pathology specified")


def render_history(
    case1: HadmCase | None,
    case2: HadmCase | None,
    label: str,
    dataset_id: str,
    min_match_length: int,
):
    """Render history of present illness with highlighting."""
    st.markdown(f"**{label}**")

    text = case1.patient_history if case1 else None
    other_text = case2.patient_history if case2 else None

    if text:
        if other_text and text != other_text:
            # Highlight matching blocks
            if dataset_id == "dataset1":
                highlighted, _ = create_highlighted_pair(text, other_text, min_match_length)
            else:
                _, highlighted = create_highlighted_pair(other_text, text, min_match_length)

            st.markdown(
                f'<div class="text-box">{highlighted}</div>',
                unsafe_allow_html=True,
            )
        else:
            # No highlighting needed
            plain_text = text.replace("\n", "<br>")
            st.markdown(
                f'<div class="text-box">{plain_text}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.warning("No history data")


def render_physical_exam(
    case1: HadmCase | None,
    case2: HadmCase | None,
    label: str,
    dataset_id: str,
    min_match_length: int,
):
    """Render physical exam text with highlighting."""
    st.markdown(f"**{label}**")

    text = case1.physical_exam_text if case1 else None
    other_text = case2.physical_exam_text if case2 else None

    if text:
        if other_text and text != other_text:
            # Highlight matching blocks
            if dataset_id == "dataset1":
                highlighted, _ = create_highlighted_pair(text, other_text, min_match_length)
            else:
                _, highlighted = create_highlighted_pair(other_text, text, min_match_length)

            st.markdown(
                f'<div class="text-box">{highlighted}</div>',
                unsafe_allow_html=True,
            )
        else:
            # No highlighting needed
            plain_text = text.replace("\n", "<br>")
            st.markdown(
                f'<div class="text-box">{plain_text}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.warning("No physical exam data")


def render_radiology(
    case1: HadmCase | None,
    case2: HadmCase | None,
    label: str,
    dataset_id: str,
    min_match_length: int,
):
    """Render radiology reports with highlighting."""
    st.markdown(f"**{label}**")

    reports = case1.radiology_reports if case1 else []
    other_reports = case2.radiology_reports if case2 else []

    if reports:
        for i, report in enumerate(reports):
            with st.expander(f"Report {i + 1}: {report.exam_name or 'Unknown'}", expanded=False):
                st.write(f"**Note ID:** {report.note_id}")
                if report.region:
                    st.write(f"**Region:** {report.region}")
                if report.modality:
                    st.write(f"**Modality:** {report.modality}")
                if report.text:
                    # Try to find matching report in other dataset by note_id
                    other_text = None
                    for other_report in other_reports:
                        if other_report.note_id == report.note_id and other_report.text:
                            other_text = other_report.text
                            break

                    if other_text and report.text != other_text:
                        # Highlight matching blocks
                        if dataset_id == "dataset1":
                            highlighted, _ = create_highlighted_pair(
                                report.text, other_text, min_match_length
                            )
                        else:
                            _, highlighted = create_highlighted_pair(
                                other_text, report.text, min_match_length
                            )

                        st.markdown(
                            f'<div class="text-box" style="height: 200px;">{highlighted}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        # No highlighting needed
                        plain_text = report.text.replace("\n", "<br>")
                        st.markdown(
                            f'<div class="text-box" style="height: 200px;">{plain_text}</div>',
                            unsafe_allow_html=True,
                        )
    else:
        st.info("No radiology reports")


def render_ground_truth(case: HadmCase, label: str):
    """Render ground truth data."""
    st.markdown(f"**{label}**")
    if case.ground_truth:
        st.write(f"**Primary Diagnosis:** {case.ground_truth.primary_diagnosis or 'N/A'}")
        if case.ground_truth.treatments:
            st.write("**Treatments:**")
            for treatment in case.ground_truth.treatments:
                if treatment.icd_code:
                    st.write(f"- {treatment.title} (ICD: {treatment.icd_code})")
                else:
                    st.write(f"- {treatment.title}")
        else:
            st.write("**Treatments:** None")
    else:
        st.warning("No ground truth data")


def render_lab_results(case: HadmCase, label: str):
    """Render lab results in an expandable table."""
    st.markdown(f"**{label}**")

    if case.lab_results:
        with st.expander(f"Lab Results ({len(case.lab_results)} tests)", expanded=False):
            # Create a table-like display
            lab_data = []
            for lab in case.lab_results:
                ref_range = ""
                if lab.ref_range_lower is not None and lab.ref_range_upper is not None:
                    ref_range = f"{lab.ref_range_lower} - {lab.ref_range_upper}"
                elif lab.ref_range_lower is not None:
                    ref_range = f">= {lab.ref_range_lower}"
                elif lab.ref_range_upper is not None:
                    ref_range = f"<= {lab.ref_range_upper}"

                lab_data.append(
                    {
                        "Test": lab.test_name,
                        "Value": lab.value or "N/A",
                        "Ref Range": ref_range,
                        "Fluid": lab.fluid or "N/A",
                        "Category": lab.category or "N/A",
                    }
                )

            st.dataframe(lab_data, use_container_width=True, height=300)
    else:
        st.info("No lab results")


def render_microbiology(case: HadmCase, label: str):
    """Render microbiology events in an expandable section."""
    st.markdown(f"**{label}**")

    if case.microbiology_events:
        with st.expander(
            f"Microbiology Events ({len(case.microbiology_events)} events)", expanded=False
        ):
            for i, event in enumerate(case.microbiology_events):
                st.markdown(f"**Event {i + 1}**")
                st.write(f"- **Test:** {event.test_name or 'N/A'}")
                st.write(f"- **Specimen Type:** {event.spec_type_desc or 'N/A'}")
                st.write(f"- **Organism:** {event.organism_name or 'N/A'}")
                if event.comments:
                    st.write(f"- **Comments:** {event.comments}")
                if event.charttime:
                    st.write(f"- **Chart Time:** {event.charttime}")
                st.divider()
    else:
        st.info("No microbiology events")


def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="Benchmark Comparison Tool", layout="wide")
    st.title("Benchmark Dataset Comparison Tool")
    st.markdown("Compare cases from **benchmark_data.json** vs **benchmark_data_cdm_v1.json**")

    # File paths
    base_path = Path("database/output")
    file1_path = base_path / "benchmark_data.json"
    file2_path = base_path / "benchmark_data_cdm_v1.json"

    # Load datasets at startup
    if "dataset1" not in st.session_state:
        with st.spinner("Loading benchmark_data.json..."):
            try:
                st.session_state.dataset1 = load_benchmark_dataset(str(file1_path))
                logger.info(f"Loaded {len(st.session_state.dataset1)} cases from dataset 1")
            except Exception as e:
                st.error(f"Error loading {file1_path}: {e}")
                logger.error(f"Error loading dataset 1: {e}")
                st.session_state.dataset1 = BenchmarkDataset(cases=[])

    if "dataset2" not in st.session_state:
        with st.spinner("Loading benchmark_data_cdm_v1.json..."):
            try:
                st.session_state.dataset2 = load_benchmark_dataset(str(file2_path))
                logger.info(f"Loaded {len(st.session_state.dataset2)} cases from dataset 2")
            except Exception as e:
                st.error(f"Error loading {file2_path}: {e}")
                logger.error(f"Error loading dataset 2: {e}")
                st.session_state.dataset2 = BenchmarkDataset(cases=[])

    # Get hadm_ids from both datasets
    hadm_ids_1 = {case.hadm_id for case in st.session_state.dataset1.cases}
    hadm_ids_2 = {case.hadm_id for case in st.session_state.dataset2.cases}
    all_hadm_ids = sorted(hadm_ids_1.union(hadm_ids_2))

    if not all_hadm_ids:
        st.error("No cases found in either dataset")
        return

    # Initialize current index in session state
    if "current_case_index" not in st.session_state:
        st.session_state.current_case_index = 0

    # Display dataset stats
    st.info(
        f"📊 Dataset 1: {len(hadm_ids_1)} cases | "
        f"Dataset 2: {len(hadm_ids_2)} cases | "
        f"Union: {len(all_hadm_ids)} unique hadm_ids | "
        f"Showing {st.session_state.current_case_index + 1} of {len(all_hadm_ids)}"
    )

    # Navigation controls
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("◀ Previous", use_container_width=True):
            if st.session_state.current_case_index > 0:
                st.session_state.current_case_index -= 1
                st.rerun()

    with col2:
        current_hadm_id = all_hadm_ids[st.session_state.current_case_index]

        selected_hadm_id = st.number_input(
            "Hospital Admission ID (hadm_id)",
            min_value=min(all_hadm_ids),
            max_value=max(all_hadm_ids),
            value=current_hadm_id,
            step=1,
            help="Enter a hadm_id or use Previous/Next buttons to navigate",
        )

        # Check if user manually changed the hadm_id
        if selected_hadm_id != current_hadm_id:
            if selected_hadm_id in all_hadm_ids:
                st.session_state.current_case_index = all_hadm_ids.index(selected_hadm_id)
            else:
                # Find closest hadm_id
                closest_idx = min(
                    range(len(all_hadm_ids)),
                    key=lambda i: abs(all_hadm_ids[i] - selected_hadm_id),
                )
                st.session_state.current_case_index = closest_idx
            st.rerun()

        hadm_id = all_hadm_ids[st.session_state.current_case_index]

    with col3:
        if st.button("Next ▶", use_container_width=True):
            if st.session_state.current_case_index < len(all_hadm_ids) - 1:
                st.session_state.current_case_index += 1
                st.rerun()

    # Get cases for current hadm_id
    case1 = next((c for c in st.session_state.dataset1.cases if c.hadm_id == hadm_id), None)
    case2 = next((c for c in st.session_state.dataset2.cases if c.hadm_id == hadm_id), None)

    # Display availability
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if case1:
            st.success("✓ Case found in benchmark_data.json")
        else:
            st.warning("✗ Case NOT found in benchmark_data.json")
    with col2:
        if case2:
            st.success("✓ Case found in benchmark_data_cdm_v1.json")
        else:
            st.warning("✗ Case NOT found in benchmark_data_cdm_v1.json")

    # Slider for minimum match length
    min_match_length = st.slider(
        "Minimum match length for highlighting",
        min_value=10,
        max_value=100,
        value=20,
        step=5,
        help="Minimum number of characters for a text block to be highlighted as a match",
    )

    # Apply CSS for highlighting
    st.markdown(generate_color_scheme_css(), unsafe_allow_html=True)

    # Main comparison section
    st.divider()
    st.subheader(f"Case Comparison: hadm_id {hadm_id}")
    st.info(
        "Matching text blocks between the two datasets are highlighted with the same color. "
        "Adjust the minimum match length slider to show more or fewer matches. "
        "Colors automatically adapt to your system's light/dark mode."
    )

    col1, col2 = st.columns(2)

    # Left column: benchmark_data.json
    with col1:
        st.markdown("## 📋 benchmark_data.json")
        if case1:
            render_pathology(case1, "Pathology")
            st.divider()
            render_demographics(case1, "Demographics")
            st.divider()
            render_history(case1, case2, "History of Present Illness", "dataset1", min_match_length)
            st.divider()
            render_physical_exam(case1, case2, "Physical Exam", "dataset1", min_match_length)
            st.divider()
            render_radiology(case1, case2, "Radiology Reports", "dataset1", min_match_length)
            st.divider()
            render_ground_truth(case1, "Ground Truth")
        else:
            st.info("No data for this case in dataset 1")

    # Right column: benchmark_data_cdm_v1.json
    with col2:
        st.markdown("## 📋 benchmark_data_cdm_v1.json")
        if case2:
            render_pathology(case2, "Pathology")
            st.divider()
            render_demographics(case2, "Demographics")
            st.divider()
            render_history(case2, case1, "History of Present Illness", "dataset2", min_match_length)
            st.divider()
            render_physical_exam(case2, case1, "Physical Exam", "dataset2", min_match_length)
            st.divider()
            render_radiology(case2, case1, "Radiology Reports", "dataset2", min_match_length)
            st.divider()
            render_ground_truth(case2, "Ground Truth")
        else:
            st.info("No data for this case in dataset 2")

    # Lab results and microbiology at the bottom (side by side)
    st.divider()
    st.subheader("Lab Results & Microbiology")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### benchmark_data.json")
        if case1:
            render_lab_results(case1, "Lab Results")
            st.markdown("---")
            render_microbiology(case1, "Microbiology Events")
        else:
            st.info("No data for this case")

    with col2:
        st.markdown("### benchmark_data_cdm_v1.json")
        if case2:
            render_lab_results(case2, "Lab Results")
            st.markdown("---")
            render_microbiology(case2, "Microbiology Events")
        else:
            st.info("No data for this case")


if __name__ == "__main__":
    main()
