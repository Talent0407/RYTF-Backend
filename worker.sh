#!/bin/sh

celery -A config.celery_app worker --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler -l info
