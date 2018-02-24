#!/usr/bin/env python
##
## Copyright (c) 2017, 2018 RockNSM.
##
## This file is part of RockNSM
## (see http://rocknsm.io).
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
##
from application import Application
import os

my_app = Application(environment=os.environ)
celery = my_app.celery()

import tasks

app = my_app.flask_app
if __name__ == '__main__':
    app.logger.info("Running {}".format(app.flask_app.name))
    app.run()
