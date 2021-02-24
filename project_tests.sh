#!/bin/bash
set -e
source venv/bin/activate
pip install coveralls
coverage run -m pytest
COVERALLS_REPO_TOKEN=$(cat /etc/coveralls/tokens/elife-cleaner) coveralls
