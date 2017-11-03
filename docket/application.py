#!/usr/bin/env python
from flask import Flask, jsonify
from flask_script import Manager
from celery import Celery

from common.exceptions import HTTPException

import yaml
import os
import logging

# Structure inspired by https://www.twilio.com/docs/tutorials/appointment-reminders-python-flask#the-application-structure
class Application(object):
    def __init__(self, config, debug=True):
        self.flask_app = Flask(__name__)
        self.debug = debug
        if debug:
            self.flask_app.setLevel(logging.DEBUG)
        self._configure_app(config)
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
                broker=app.config['CELERY_BROKER_URL'])

        celery.conf.update(app.config)

        TaskBase = celery.Task
        class ContextTask(TaskBase):
            abstract = True

            def _call_(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

        celery.Task = ContextTask

        return celery

    def manager(self):
        return Manager(self.flask_app)

    def _set_blueprints(self):
        from api import api_bp
        self.flask_app.register_blueprint(api_bp)

    def _configure_app(self, env):
        _conf_path = env.get('APP_CONFIG', 'devel')
        self.flask_app.logger.info("Loading config: %s" % _conf_path)
        _config = {}
        if _conf_path:
            self.flask_app.config['APP_CONFIG'] = os.path.join(
                '/etc/docket/', ("%s.yaml" % _conf_path))

            with open(self.flask_app.config['APP_CONFIG']) as f:
                _config = yaml.load(f.read())
            self.flask_app.logger.debug("Loaded YAML:\n%s" % _config)

            self.flask_app.config.update(_config)

        celery_url = self.flask_app.config['CELERY_URL']
        spool_dir  = self.flask_app.config['SPOOL_DIR']
        # Update file config with environment overrides
        celery_url = env.get('CELERY_URL', celery_url)

        self.flask_app.config['CELERY_BROKER_URL'] = env.get(
                'REDIS_URL', celery_url)
        self.flask_app.config['CELERY_RESULT_BACKEND'] = env.get(
                'REDIS_URL', celery_url)
        self.flask_app.secret_key = env.get('SECRET_KEY')
        self.flask_app.spool_dir = env.get('SPOOL_DIR', spool_dir)

    def start_app(self):
        self.flask_app.run(debug=self.debug)
