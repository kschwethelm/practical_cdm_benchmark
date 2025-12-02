"""Streamlit UI for comparing clinical data from different database tables."""

import difflib

import streamlit as st
from loguru import logger

from cdm.database.connection import db_cursor

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
    Find matching text blocks between two strings.

    Args:
        text1: First text string
        text2: Second text string
        min_length: Minimum length of matching blocks to consider

    Returns:
        List of (i, j, n) tuples where text1[i:i+n] == text2[j:j+n]
    """
    if not text1 or not text2:
        return []

    matcher = difflib.SequenceMatcher(None, text1, text2)
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


def create_colored_comparison(
    text1: str, text2: str, text3: str, min_match_length: int = 20
) -> tuple[str, str, str]:
    """
    Create color-highlighted versions of three texts showing matching blocks.

    Args:
        text1: First text (discharge note)
        text2: Second text (extracted field)
        text3: Third text (cdm_v1 field)
        min_match_length: Minimum length of matching blocks to highlight

    Returns:
        Tuple of (highlighted_text1, highlighted_text2, highlighted_text3)
    """
    if not text1:
        text1 = ""
    if not text2:
        text2 = ""
    if not text3:
        text3 = ""

    # Find all matching blocks between pairs
    matches_1_2 = find_matching_blocks(text1, text2, min_match_length)
    matches_1_3 = find_matching_blocks(text1, text3, min_match_length)
    matches_2_3 = find_matching_blocks(text2, text3, min_match_length)

    # Create highlight lists for each text
    highlights_1: list[tuple[int, int, str]] = []
    highlights_2: list[tuple[int, int, str]] = []
    highlights_3: list[tuple[int, int, str]] = []

    color_idx = 0

    # Add highlights for text1-text2 matches
    for i, j, n in matches_1_2:
        # Use CSS variable that will adapt to light/dark mode
        color = f"var(--highlight-color-{color_idx % len(COLOR_VARS)})"
        highlights_1.append((i, i + n, color))
        highlights_2.append((j, j + n, color))
        color_idx += 1

    # Add highlights for text1-text3 matches
    for i, k, n in matches_1_3:
        color = f"var(--highlight-color-{color_idx % len(COLOR_VARS)})"
        highlights_1.append((i, i + n, color))
        highlights_3.append((k, k + n, color))
        color_idx += 1

    # Add highlights for text2-text3 matches
    for j, k, n in matches_2_3:
        color = f"var(--highlight-color-{color_idx % len(COLOR_VARS)})"
        highlights_2.append((j, j + n, color))
        highlights_3.append((k, k + n, color))
        color_idx += 1

    # Merge overlapping highlights and apply to text
    highlighted_1 = highlight_text(text1, merge_highlights(highlights_1))
    highlighted_2 = highlight_text(text2, merge_highlights(highlights_2))
    highlighted_3 = highlight_text(text3, merge_highlights(highlights_3))

    return highlighted_1, highlighted_2, highlighted_3


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
        height: 600px;
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


def get_table_columns(schema: str, table: str) -> list[str]:
    """Get column names for a specific table."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        columns = [row[0] for row in cur.fetchall()]
    return columns


def get_discharge_note(hadm_id: int) -> str | None:
    """Get discharge note text from cdm_note.discharge table."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT text
            FROM cdm_note.discharge
            WHERE hadm_id = %s
            """,
            (hadm_id,),
        )
        result = cur.fetchone()
        return result[0] if result else None


def get_extracted_field(hadm_id: int, column_name: str) -> str | None:
    """Get extracted field from cdm_note_extract.discharge_free_text table."""
    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT {column_name}
            FROM cdm_note_extract.discharge_free_text
            WHERE hadm_id = %s
            """,
            (hadm_id,),
        )
        result = cur.fetchone()
        return result[0] if result else None


def get_cdm_v1_field(hadm_id: int, column_name: str, table_name: str) -> str | None:
    """Get field from cdm_v1 schema table."""
    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT {column_name}
            FROM cdm_v1.{table_name}
            WHERE hadm_id = %s
            """,
            (hadm_id,),
        )
        result = cur.fetchone()
        return result[0] if result else None


def get_union_hadm_ids(cdm_v1_table: str | None = None) -> list[int]:
    """
    Get union of hadm_ids from all relevant tables.

    Args:
        cdm_v1_table: Optional specific cdm_v1 table to include in union

    Returns:
        Sorted list of unique hadm_ids
    """
    with db_cursor() as cur:
        # Start with hadm_ids from discharge notes
        queries = [
            "SELECT DISTINCT hadm_id FROM cdm_note.discharge",
            "SELECT DISTINCT hadm_id FROM cdm_note_extract.discharge_free_text",
        ]

        # Add cdm_v1 table if specified
        if cdm_v1_table:
            queries.append(f"SELECT DISTINCT hadm_id FROM cdm_v1.{cdm_v1_table}")

        # Union all queries
        union_query = " UNION ".join(queries) + " ORDER BY hadm_id"

        cur.execute(union_query)
        hadm_ids = [row[0] for row in cur.fetchall()]

    logger.info(f"Found {len(hadm_ids)} unique hadm_ids across tables")
    return hadm_ids


def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="Clinical Data Comparison", layout="wide")
    st.title("Clinical Data Comparison Tool")
    st.markdown("Compare clinical text data from different database tables")

    # Get available cdm_v1 tables first (needed for loading hadm_ids)
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'cdm_v1'
                ORDER BY table_name
                """
            )
            cdm_v1_tables = [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching cdm_v1 tables: {e}")
        cdm_v1_tables = []

    # Load all hadm_ids at startup
    if "hadm_ids" not in st.session_state:
        with st.spinner("Loading hadm_ids from database..."):
            try:
                # Load hadm_ids from all tables (without specific cdm_v1 table filter)
                st.session_state.hadm_ids = get_union_hadm_ids()
                logger.info(f"Loaded {len(st.session_state.hadm_ids)} hadm_ids at startup")
            except Exception as e:
                st.error(f"Error loading hadm_ids: {e}")
                logger.error(f"Error loading hadm_ids: {e}")
                st.session_state.hadm_ids = []

    # Display total hadm_ids available
    if st.session_state.hadm_ids:
        st.info(f"📊 {len(st.session_state.hadm_ids)} hadm_ids available. Use +/- to navigate.")

    # Input field for hadm_id with navigation via +/-
    hadm_id = st.number_input(
        "Hospital Admission ID (hadm_id)",
        min_value=min(st.session_state.hadm_ids) if st.session_state.hadm_ids else 1,
        max_value=max(st.session_state.hadm_ids) if st.session_state.hadm_ids else 999999,
        value=st.session_state.hadm_ids[0] if st.session_state.hadm_ids else 1,
        step=1,
        help="Enter a hadm_id or use +/- buttons to navigate through available IDs",
    )

    # Get available columns for dropdowns
    try:
        extract_columns = get_table_columns("cdm_note_extract", "discharge_free_text")
        # Remove hadm_id from selectable columns
        extract_columns = [col for col in extract_columns if col != "hadm_id"]
    except Exception as e:
        logger.error(f"Error fetching cdm_note_extract.discharge_free_text columns: {e}")
        extract_columns = []

    # Dropdowns for column selection
    col1, col2 = st.columns(2)

    with col1:
        selected_extract_column = st.selectbox(
            "Select column from cdm_note_extract.discharge_free_text",
            options=extract_columns,
            help="Choose which extracted field to display",
        )

    with col2:
        selected_cdm_v1_table = st.selectbox(
            "Select table from cdm_v1 schema",
            options=cdm_v1_tables,
            help="Choose which cdm_v1 table to query",
        )

    # Get columns for selected cdm_v1 table
    cdm_v1_columns = []
    if selected_cdm_v1_table:
        try:
            cdm_v1_columns = get_table_columns("cdm_v1", selected_cdm_v1_table)
            cdm_v1_columns = [col for col in cdm_v1_columns if col != "hadm_id"]
        except Exception as e:
            logger.error(f"Error fetching cdm_v1.{selected_cdm_v1_table} columns: {e}")

    selected_cdm_v1_column = st.selectbox(
        f"Select column from cdm_v1.{selected_cdm_v1_table}",
        options=cdm_v1_columns,
        help="Choose which field to display from the selected table",
    )

    # Slider for minimum match length
    min_match_length = st.slider(
        "Minimum match length for highlighting",
        min_value=10,
        max_value=100,
        value=20,
        step=5,
        help="Minimum number of characters for a text block to be highlighted as a match",
    )

    # Fetch and display button
    if st.button("Compare Data", type="primary"):
        if not hadm_id:
            st.warning("Please enter a valid hadm_id")
            return

        if not selected_extract_column or not selected_cdm_v1_column:
            st.warning("Please select columns from both tables")
            return

        # Fetch all three pieces of data
        with st.spinner("Fetching data from database..."):
            try:
                discharge_text = get_discharge_note(hadm_id)
                extracted_text = get_extracted_field(hadm_id, selected_extract_column)
                cdm_v1_text = get_cdm_v1_field(
                    hadm_id, selected_cdm_v1_column, selected_cdm_v1_table
                )
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                logger.error(f"Database error for hadm_id {hadm_id}: {e}")
                return

        # Apply color highlighting to matching text blocks
        with st.spinner("Analyzing text matches..."):
            highlighted_1, highlighted_2, highlighted_3 = create_colored_comparison(
                discharge_text or "",
                extracted_text or "",
                cdm_v1_text or "",
                min_match_length=min_match_length,
            )

        # Display results in three columns
        st.divider()
        st.subheader(f"Comparison Results for hadm_id: {hadm_id}")
        st.info(
            "Matching text blocks are highlighted with the same color across columns. "
            "Adjust the minimum match length slider to show more or fewer matches. "
            "Colors automatically adapt to your system's light/dark mode."
        )

        # CSS for scrollable boxes and color scheme that adapts to dark mode
        st.markdown(generate_color_scheme_css(), unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### cdm_note.discharge (text)")
            if discharge_text:
                st.markdown(
                    f'<div class="text-box">{highlighted_1}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No discharge note found")

        with col2:
            st.markdown(f"### cdm_note_extract.discharge_free_text ({selected_extract_column})")
            if extracted_text:
                st.markdown(
                    f'<div class="text-box">{highlighted_2}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"No data found for {selected_extract_column}")

        with col3:
            st.markdown(f"### cdm_v1.{selected_cdm_v1_table} ({selected_cdm_v1_column})")
            if cdm_v1_text:
                st.markdown(
                    f'<div class="text-box">{highlighted_3}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"No data found for {selected_cdm_v1_column}")


if __name__ == "__main__":
    main()
