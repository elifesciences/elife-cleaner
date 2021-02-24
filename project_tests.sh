#!/bin/bash
set -e
. mkvenv.sh
source venv/bin/activate
pip install -r requirements.txt
pip install coveralls
coverage run -m pytest
