#!/bin/bash
# Run script for the AI agent orchestrator
# This sets up the Python path correctly

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(dirname "$(pwd)")"
python orchestrator/main.py "$@"
