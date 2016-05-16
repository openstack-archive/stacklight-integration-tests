#!/bin/bash
#
# Script to setup a Python virtual environment with all the dependencies
# installed

set -e

# Initialize variables
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH=${VENV_PATH:-"${BASE_DIR}"/venv-stacklight-tests}
FUELQA_GITREF=${FUELQA_GITREF:-stable/8.0}
VIRTUALENV_BINARY=$(which virtualenv)

if [[ -z "${VIRTUALENV_BINARY}" ]]; then
    echo 'Cannot find the virtualenv executable!'
    echo 'You should install it either using pip or you distribution package manager.'
    exit 1
fi

if [ ! -x "$VENV_PATH"/bin/activate ]; then
    "$VIRTUALENV_BINARY" "$VENV_PATH"
fi

. "$VENV_PATH"/bin/activate

# Always upgrade to the latest version of pip
pip install -U pip

# Install fuel-qa in the virtual environment
FUELQA_GITREF=${FUELQA_GITREF:-stable/8.0}
echo "Checking out fuel-qa/$FUELQA_GITREF"
FUELQA_DIR=$(mktemp -d)
git clone https://github.com/openstack/fuel-qa.git -- "$FUELQA_DIR"

pushd "$FUELQA_DIR"
git checkout "$FUELQA_GITREF"

cp "${BASE_DIR}"/{MANIFEST.in,setup.py} ./

python setup.py sdist
pip install dist/fuelweb_test*.tar.gz

# Clean up stuff
popd
rm -rf "$FUELQA_DIR"

# Install project's dependencies
pip install -rrequirements.txt

echo
echo
echo "The setup is now complete."
echo "Run this command in your shell to activate your Python virtual environment:"
echo "  . $VENV_PATH/bin/activate"
