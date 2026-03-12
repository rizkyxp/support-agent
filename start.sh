#!/bin/bash
echo "Starting Support Agent Control Panel..."

# Function to check command presence
check_command() {
    command -v "$1" >/dev/null 2>&1
}

# Determine python command
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Setup Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Use venv python and pip
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

echo "Installing requirements..."
$VENV_PIP install -r requirements.txt

echo "Starting the Web UI Control Panel..."
echo "Open your browser at http://localhost:8000 to use the local control panel."
echo ""
$VENV_PYTHON -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000 --reload
