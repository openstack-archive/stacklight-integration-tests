#!/bin/bash
#
# Script to setup a Python virtual environment (if needed) and install all the
# project's dependencies

set -e

# Initialize the variables
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH=${VENV_PATH:-"${BASE_DIR}"/venv-stacklight-tests}
FUELQA_GITREF=${FUELQA_GITREF:-stable/mitaka}

# Create the virtual environment if it doesn't exist yet
if [[ ! -f "$VENV_PATH"/bin/activate ]]; then
    if ! which virtualenv; then
        echo 'Cannot find the virtualenv executable!'
        echo 'You should install it either using pip or your distribution package manager.'
        exit 1
    fi

    echo "Creating virtual environment in '$VENV_PATH'"
    virtualenv "$VENV_PATH"
    . "$VENV_PATH"/bin/activate

    # Always upgrade to the latest version of pip
    pip install -U pip
else
    . "$VENV_PATH"/bin/activate
fi

echo "Using virtual environment at '$VIRTUAL_ENV'"

if [[ "$(pip show fuelweb-test)" == "" ]]; then
    # Install fuel-qa in the virtual environment
    echo "Checking out fuel-qa, reference: $FUELQA_GITREF"
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
fi

# Install the project's dependencies
pip install -r"${BASE_DIR}/../../requirements.txt"

echo
echo
echo "The setup is now complete."
echo "Run this command in your shell to activate your Python virtual environment:"
echo "  . $VIRTUAL_ENV/bin/activate"
