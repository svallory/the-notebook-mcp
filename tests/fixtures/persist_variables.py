"""
Helper module to persist variables between notebook executions.
"""

import pickle
import os


def save_variable(variable, name, file_path=None):
    """
    Save a variable to a pickle file.

    Args:
        variable: The variable to save
        name: The name of the variable (used as filename if file_path not provided)
        file_path: Optional custom file path
    """
    if file_path is None:
        file_path = f"{name}.pkl"

    with open(file_path, "wb") as f:
        pickle.dump(variable, f)

    return file_path


def load_variable(name, file_path=None):
    """
    Load a variable from a pickle file.

    Args:
        name: The name of the variable (used as filename if file_path not provided)
        file_path: Optional custom file path

    Returns:
        The loaded variable or None if file doesn't exist
    """
    if file_path is None:
        file_path = f"{name}.pkl"

    if not os.path.exists(file_path):
        return None

    with open(file_path, "rb") as f:
        return pickle.load(f)
