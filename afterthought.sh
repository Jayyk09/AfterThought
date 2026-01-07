#!/bin/bash

# AfterThought shell wrapper
# This script activates the virtual environment and runs the afterthought CLI

# CONFIGURE THESE PATHS
VENV_PATH="$HOME/Desktop/Projects/AfterThought/venv"
PROJECT_PATH="$HOME/Desktop/Projects/AfterThought"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Change to project directory (needed for .env file)
cd "$PROJECT_PATH"

# Run afterthought with all passed arguments
python -m afterthought.cli "$@"

# Exit code from the Python command
exit $?
