#!/bin/bash

DOCKET_DIR="$(readlink -f $(pwd))/docket"
echo ${DOCKET_DIR}
celery worker --workdir "${DOCKET_DIR}" --app manage.celery -l info

