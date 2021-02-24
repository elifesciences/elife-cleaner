#!/bin/bash
set -e
source venv/bin/activate
pip install coveralls
COVERALLS_REPO_TOKEN=$(cat /etc/coveralls/tokens/elife-cleaner) coveralls
