#!/bin/bash
set -e
source venv/bin/activate
pip install coveralls
coverage run -m pytest
