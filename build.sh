#!/bin/bash
set -e
pip install --quiet --no-cache-dir --requirement requirements.txt
pip list --outdated
pylint *.py
coverage run -m pytest tests
coverage report -m
uname -n | grep -v penguin && docker build --tag verjaardagskalender .
