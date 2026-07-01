#!/usr/bin/env bash
set -o errexit

pip install -r requirements/production.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py create_demo_data