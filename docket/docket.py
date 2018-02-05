#!/usr/bin/env python
from application import Application
import os

app = Application(environment=os.environ)
celery = app.celery()

import tasks

if __name__ == '__main__':
    Config.logger.info("Running {}".format(app.name))
    app.run()
