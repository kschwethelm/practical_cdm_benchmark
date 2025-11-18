"""Convert pickle files to JSON format.

This script searches for pickle files in a source directory and converts them
to JSON format in a target directory. Handles pandas DataFrames by converting
them to records format.
"""

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger


def is_nan(value: Any) -> bool:
    """Check if a value is NaN (handles various types).

    Args:
        value: Value to check

    Returns:
        True if value is NaN, False otherwise
    """
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False


def serialize_data(data: Any) -> Any:
    """Convert data to JSON-serializable format.

    Args:
        data: Data to serialize (can be DataFrame, dict, list, etc.)

    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to list of records (dictionaries)
        # Replace NaN with None (which becomes null in JSON)
        return data.where(pd.notna(data), None).to_dict(orient="records")
    elif isinstance(data, pd.Series):
        # Convert Series to list, replacing NaN with None
        return data.where(pd.notna(data), None).tolist()
    elif isinstance(data, dict):
        # Recursively handle nested dictionaries
        return {key: serialize_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Recursively handle lists
        return [serialize_data(item) for item in data]
    elif is_nan(data):
        # Convert any NaN values to None (becomes null in JSON)
        return None
    else:
        # Return as-is for primitives
        return data


def convert_pkl_to_json(source_folder: Path, target_folder: Path) -> None:
    """Convert all pickle files in source folder to JSON in target folder.

    Args:
        source_folder: Directory containing .pkl files to convert
        target_folder: Directory where JSON files will be saved
    """
    # Ensure target folder exists
    target_folder.mkdir(parents=True, exist_ok=True)

    # Find all pkl files in source folder
    pkl_files = list(source_folder.glob("*.pkl"))

    if not pkl_files:
        logger.warning(f"No .pkl files found in {source_folder}")
        return

    logger.info(f"Found {len(pkl_files)} pickle file(s) to convert")

    # Convert each pickle file to JSON
    for pkl_file in pkl_files:
        try:
            # Load pickle file
            with open(pkl_file, "rb") as f:
                data = pickle.load(f)

            # Convert to JSON-serializable format
            serializable_data = serialize_data(data)

            # Save as JSON
            json_file = target_folder / (pkl_file.stem + ".json")
            with open(json_file, "w") as f:
                json.dump(serializable_data, f, indent=2)

            logger.info(f"Converted {pkl_file.name} -> {json_file.name}")

        except Exception as e:
            logger.error(f"Failed to convert {pkl_file.name}: {e}")


def main() -> None:
    """Main entry point for pickle to JSON conversion."""
    source_folder = Path("/srv/mimic/cdm_v1/")
    target_folder = Path("/srv/student/cdm_v1/")

    logger.info(f"Source folder: {source_folder}")
    logger.info(f"Target folder: {target_folder}")

    convert_pkl_to_json(source_folder, target_folder)

    logger.info("Conversion complete")


if __name__ == "__main__":
    main()
