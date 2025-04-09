#!/usr/bin/env python3
"""Script to format all Python files in the project using isort and black."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, explanation=None):
    """Run a shell command and print its output."""
    if explanation:
        print(f"# {explanation}")
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def format_directory(directory, exclude_dirs=None):
    """Format all Python files in a directory using isort and black."""
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", ".git", ".cursor", ".unused"]

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    if not python_files:
        print(f"No Python files found in {directory}")
        return True

    print(f"Found {len(python_files)} Python files to format")

    # Run isort to sort imports
    isort_success = run_command(
        ["isort", "--profile=black", "--line-length=100"] + python_files,
        "Sorting imports with isort",
    )

    # Run black to format code
    black_success = run_command(
        ["black", "--line-length=100"] + python_files, "Formatting code with black"
    )

    return isort_success and black_success


def create_pylintrc(directory):
    """Create a minimal .pylintrc file for the project."""
    pylintrc_path = os.path.join(directory, ".pylintrc")
    if os.path.exists(pylintrc_path):
        print("Existing .pylintrc file found, skipping creation.")
        return True

    print("Creating minimal .pylintrc file...")

    # Create a basic .pylintrc file with init-hook to handle imports
    pylintrc_content = f"""[MASTER]
# Add the current directory to Python path for pylint
init-hook='import sys; sys.path.append("{directory}")'

# Pygame has dynamically created attributes, which pylint cannot detect
[TYPECHECK]
ignored-modules=pygame
ignored-classes=pygame,pygame.Surface,pygame.Rect

[FORMAT]
max-line-length=100

[MESSAGES CONTROL]
disable=
    C0111, # Missing docstring
    C0103, # Invalid name
    C0303, # Trailing whitespace (handled by black)
    C0301, # Line too long (handled by black)
    R0913, # Too many arguments
    R0914, # Too many local variables
    R0915, # Too many statements
    W0614, # Unused import from wildcard
    W0401, # Wildcard import
    W0703, # Broad except
    W0212, # Protected member access
    R0912, # Too many branches
    R0903, # Too few public methods
    R0902, # Too many instance attributes
    R0904, # Too many public methods
    R0801, # Duplicate code
    W0511, # FIXME/TODO
    W1203  # Use lazy % formatting in logging functions
"""

    try:
        with open(pylintrc_path, "w") as f:
            f.write(pylintrc_content)
        print(f"Created .pylintrc file at {pylintrc_path}")
        return True
    except Exception as e:
        print(f"Error creating .pylintrc file: {e}")
        return False


def main():
    """Main function to run the script."""
    # Default to formatting the current directory
    directory = os.getcwd()

    print(f"Formatting Python code in {directory}")

    # Check if isort and black are installed
    try:
        subprocess.run(["isort", "--version"], check=True, capture_output=True, text=True)
        subprocess.run(["black", "--version"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: isort or black not found. Please install them:")
        print("pip install isort black")
        return 1

    # Create .pylintrc file
    create_pylintrc(directory)

    # Format the directory
    if format_directory(directory):
        print("Code formatting completed successfully")
        return 0
    else:
        print("Code formatting failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
