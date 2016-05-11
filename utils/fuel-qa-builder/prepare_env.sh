#!/bin/bash

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

pip install -U pip || true

VIRTUALENV_EXIST=`dpkg -l | grep python-virtualenv || pip list | grep virtualenv`

if [[ -z "${VIRTUALENV_EXIST}" ]]; then
    echo 'There is no virtualnev'
    pip install virtualenv || apt-get install python-virtualenv || true
fi

if [ -z "${VENV_PATH}" ]; then
    VENV_PATH="${BASE_DIR}"/venv-stacklight-tests
fi

virtualenv "${VENV_PATH}" || true

. "${VENV_PATH}"/bin/activate



mkdir tmp && cd tmp

git clone https://github.com/openstack/fuel-qa.git && cd fuel-qa && git checkout stable/8.0 || true

cp "${BASE_DIR}"/MANIFEST.in  ./ && cp "${BASE_DIR}"/setup.py ./

python setup.py sdist && pip install dist/fuelweb_test*.tar.gz && pip install -r "${BASE_DIR}"/../../requirements.txt

cd "${BASE_DIR}" && rm -rf tmp
