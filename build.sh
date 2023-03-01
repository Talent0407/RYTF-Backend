#!/bin/sh

pip install -r requirements/production.txt
python manage.py collectstatic --no-input
python manage.py migrate
