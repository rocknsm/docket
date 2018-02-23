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
from flask import Flask, jsonify
from celery import Celery

from common.exceptions import HTTPException

from config import Config
import logging

# Structure inspired by https://www.twilio.com/docs/tutorials/appointment-reminders-python-flask#the-application-structure
class Application(object):
    def __init__(self, environment=None):
        self.flask_app = Flask('docket', static_folder="static/dist", template_folder="static")

        self._configure_app(environment)
        self._set_blueprints()
        self.register_error_handlers()

    def register_error_handlers(self):

        @self.flask_app.errorhandler(HTTPException)
        def handle_invalid_usage(error):
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response

    def celery(self):
        app = self.flask_app

        celery = Celery(
                app.import_name,
                broker=Config.get('CELERY_BROKER_URL'))

        celery.conf.update(Config.config)
        TaskBase = celery.Task
        class ContextTask(TaskBase):
            abstract = True

            def _call_(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

        celery.Task = ContextTask

        return celery

#    def manager(self):
#        return Manager(self.flask_app)

    def _set_blueprints(self):
        from api import api_bp
        from ui import ui_bp
        self.flask_app.register_blueprint(api_bp, url_prefix=Config.get('WEB_ROOT', '/api'))

    def _configure_app(self, env):
        conf = env.get('DOCKET_CONF') or env.get('APP_CONF')
        config = Config.load(conf, flask_app=self.flask_app, env=env)

        celery_url = Config.get('CELERY_URL')

        if not celery_url:
            Config.logger.critical("Unable to locate 'CELERY_URL', it configures celery's broker.")
            raise Exception("Invalid configuration / Environment: "
                            "Unable to locate 'CELERY_URL', it configures the broker.")

        if not config.get('CELERY_TASK_IGNORE_RESULT'):
            config['result_backend'] = Config.get('REDIS_URL', celery_url)
        config['CELERY_BROKER_URL'] = Config.get('REDIS_URL', celery_url)

        self.flask_app.secret_key = Config.get('SECRET_KEY')
        self.flask_app.spool_dir = Config.get('SPOOL_DIR')
        Config.logger.info('Using SPOOL_DIR [{}]'.format(self.flask_app.spool_dir))

        if self.flask_app.secret_key.find('CHANGE_THIS') >= 0:
            Config.logger.warning('Insecure SECRET_KEY detected! Using a randomized key.')
            # this randomization breaks sessions, but we don't have any.
            import os
            self.flask_app.secret_key = os.urandom(57)

    def start_app(self):
        self.flask_app.run(debug=self.debug)
