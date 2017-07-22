#!/usr/bin/env python
from application import Application
from common.exceptions import InvalidUsage
import os

app = Application(os.environ, debug=False)
celery = app.celery()

import tasks

if __name__ == '__main__':
    app.run()
