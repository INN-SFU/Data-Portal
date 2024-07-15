#!/bin/sh
# Source python virtual environment
echo "Sourcing python virtual environment..."
. ams_venv/bin/activate
# Source the OpenStack environment variables
echo "Sourcing OpenStack environment variables..."
. core/connectivity/arbutus/def-rmcintos-dev-openrc.sh
# Spin up app
echo "Spinning up app..."
exec python3 "$@"
