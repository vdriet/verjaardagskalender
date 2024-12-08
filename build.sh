#!/bin/bash
set -e
export PYTHONPATH=.
pip install -r requirements.txt
pip list --outdated
pylint *.py
pytest tests
docker build --tag verjaardagskalender .
