"""Utility functions for the TUI."""
import re


def clean_file_path_input(value: str) -> str:
    """Clean file path input from drag-and-drop operations.

    macOS drag-and-drop often pastes file paths multiple times. This function
    uses regex to extract all valid file paths and returns only the first unique one.

    Args:
        value: The raw input value

    Returns:
        The cleaned file path (first unique valid path found)
    """
    if not value:
        return value

    # Extract all potential file paths from the input
    # Matches absolute paths (starting with / or ~) and relative paths with extensions
    path_pattern = r'(?:^|(?<=\s))([/~][^\s]*(?:\.csv|\.json)?|[^\s]+\.(?:csv|json))(?=\s|$)'
    matches = re.findall(path_pattern, value, re.MULTILINE)

    if not matches:
        # No paths found, just clean whitespace
        return value.strip()

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for match in matches:
        path = match.strip()
        if path and path not in seen:
            seen.add(path)
            unique_paths.append(path)

    # Return the first unique path
    return unique_paths[0] if unique_paths else value.strip()
