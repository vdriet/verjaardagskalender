#!/bin/bash
set -e
pip list --outdated
pylint *.py
docker build --tag verjaardagskalender .
