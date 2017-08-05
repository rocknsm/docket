#!/usr/bin/env python
from application import Application
import os

app = Application(os.environ, debug=False)
celery = app.celery()

import tasks

if __name__ == '__main__':
    app.run()
