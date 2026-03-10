#!/bin/bash
echo "Starting Support Agent Control Panel..."

# Function to check command presence
check_command() {
    command -v "$1" >/dev/null 2>&1
}

# Determine python command
if check_command python3; then
    PYTHON_CMD="python3"
elif check_command python; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Determine pip command
if check_command pip3; then
    PIP_CMD="pip3"
elif check_command pip; then
    PIP_CMD="pip"
else
    echo "Error: pip is not installed or not in PATH."
    exit 1
fi

echo "Installing requirements..."
$PIP_CMD install -r requirements.txt

echo "Starting the Web UI Control Panel..."
echo "Open your browser at http://localhost:8000 to use the local control panel."
echo ""
$PYTHON_CMD -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000 --reload
