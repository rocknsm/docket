#!/usr/bin/env python
from application import Application
import os

app = Application(os.environ, debug=False)
celery = app.celery()

import tasks
