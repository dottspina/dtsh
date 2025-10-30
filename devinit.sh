#!/usr/bin/env sh
# Copyright (c) 2025, Christophe Dufaza
# SPDX-License-Identifier: Apache-2.0

# Alternative to "pip install -e /path/to/dtsh[dev]",
# avoid duplicating the dtsh package (depends on IDE).

# Python3.10+
py3cmd=python3.11

# From which ZEPHYR_BASE we'll install/import the devicetree package.
zephyr_base=${ZEPHYR_BASE:-"/mnt/repos/gh/zephyrproject-rtos/zephyr"}

# Virtual environment.
venv_base=.venv-zephyr

set -e

venv_base=$(realpath "$venv_base")
python_devicetree=$(realpath "$zephyr_base/scripts/dts/python-devicetree")

echo "Virtual env: ${venv_base}"
echo "ZEPHYR_BASE: ${zephyr_base}"

echo -n 'Continue [yN]: '
read yes_no
case "$yes_no" in
	y|Y)
		;;
	*)
		echo "Goodbye."
		exit 0
		;;
esac

echo
echo "* Initializing virtual env: ${venv_base}"
$py3cmd -m venv --system-site-packages --upgrade-deps --clear "$venv_base"
. "${venv_base}/bin/activate"

echo
echo '* Downloading requirements (PyPI)'
pip install -r requirements-dev.txt

echo
echo "* Installing devicetree package from: ${python_devicetree}"
pip install "${python_devicetree}"

echo
echo "* Done."
deactivate
