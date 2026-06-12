#!/bin/bash
set -e # Stop on any error

# Check if .venv folder exists
if [ ! -d ".venv" ]; then
    source .venv/bin/activate
fi

# Upgrade pip and install requirements using the local venv binary
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r linux_requirements.txt

echo "Python environment ready at .venv"