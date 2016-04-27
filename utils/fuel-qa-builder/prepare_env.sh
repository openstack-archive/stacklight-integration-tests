#!/bin/sh
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

BASE_DIR=$(pwd)

if [ -z "${VENV_PATH}" ]; then
        VENV_PATH="$HOME/venv-stacklight-tests"
fi

virtualenv "$VENV_PATH"
echo $VENV_PATH
. $VENV_PATH/bin/activate
pip install pip --upgrade

rm -rf tmp
mkdir tmp
cd tmp
git clone https://github.com/openstack/fuel-qa.git
cd fuel-qa
git branch stable/8.0
cp "$BASE_DIR/MANIFEST.in" .
cp "$BASE_DIR/setup.py" .
python setup.py sdist
pip install dist/*.tar.gz
pip install -r "$BASE_DIR/../requirements.txt"
cd "$BASE_DIR"
rm -rf tmp
