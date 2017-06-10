#!/bin/bash

celery -A manage.celery worker -l info

