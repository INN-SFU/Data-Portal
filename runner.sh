#!/bin/sh
# Source python virtual environment
. ams_venv/bin/activate
# Source the OpenStack environment variables
. core/connectivity/arbutus/def-rmcintos-dev-openrc.sh
# Spin up app
python3 main.py
