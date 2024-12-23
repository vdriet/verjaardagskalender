#!/bin/bash
set -e
export PYTHONPATH=.
pip install -r requirements.txt
pip list --outdated
pylint *.py
coverage run -m pytest tests
coverage report -m
docker build --tag verjaardagskalender .
