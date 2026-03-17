#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=core.settings
export PYTHONPATH="$PYTHONPATH:$(pwd)/core"

python core/manage.py collectstatic --noinput
python core/manage.py migrate