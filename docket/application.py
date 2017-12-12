#!/usr/bin/env python
from flask import Flask, jsonify
from celery import Celery

from common.exceptions import HTTPException

from config import Config
import logging

# !! can't use celery decorator here - we haven't made it yet
# !! can't use add_periodic_task elsewhere - celery will have been 'finalized'
#@celery.on_after_configure.connect
#def setup_periodic_tasks(sender, **kwargs):
#    from tasks import cleanup  # !! can't import tasks here - it imports celery -> loop
#    sender.add_periodic_task(Config.get('CLEANUP_PERIOD', 3600), cleanup.s(), name='hourly cleanup')
#    Config.logger.info("Added periodic task to {}".format(str(sender)))

# Structure inspired by https://www.twilio.com/docs/tutorials/appointment-reminders-python-flask#the-application-structure
class Application(object):
    def __init__(self, config=None):
        self.flask_app = Flask('docket')

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
        self.flask_app.register_blueprint(api_bp)

    def _configure_app(self, env):
        conf = env.get('DOCKET_CONF') or env.get('APP_CONF')
        config = Config.load(conf, flask_app=self.flask_app)

        celery_url = env.get('CELERY_URL', config['CELERY_URL'])

        if not celery_url:
            Config.logger.critical("Unable to locate 'CELERY_URL', it configures the broker.")
            raise Exception("Invalid configuration / Environment: "
                            "Unable to locate 'CELERY_URL', it configures the broker.")

        if not config.get('CELERY_TASK_IGNORE_RESULT'):
            config['result_backend']    = env.get('REDIS_URL', celery_url)
        config['CELERY_BROKER_URL']     = env.get('REDIS_URL', celery_url)

        # Update file config with environment overrides
        self.flask_app.secret_key       = env.get('SECRET_KEY', config['SECRET_KEY'])
        self.flask_app.spool_dir        = env.get('SPOOL_DIR',  config['SPOOL_DIR'])
        Config.logger.info('Using SPOOL_DIR [{}]'.format(self.flask_app.spool_dir))

        if self.flask_app.secret_key.find('CHANGE_THIS') >= 0:
            Config.logger.warning('Insecure SECRET_KEY detected! Using a randomized key.')
            # this randomization breaks sessions, but we don't have any.
            import os
            self.flask_app.secret_key   = os.urandom(57)

    def start_app(self):
        self.flask_app.run(debug=self.debug)

