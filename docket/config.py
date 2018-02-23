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
from __future__ import print_function
# A central location for the config dictionary
#   see application for initialization
import redis
import yaml
import os
import logging
import sys

levels = {
    'debug'  :logging.DEBUG,
    'info'   :logging.INFO,
    'warn'   :logging.WARNING,
    'warning':logging.WARNING,
    'error'  :logging.ERROR,
    'crit'   :logging.CRITICAL,
}
log_level = lambda x: levels.get(x, logging.INFO) if type(x) is str else int(x)

class Config:
    """ finds, loads, and provides access to config from FILENAME.yaml
        Verifies configuration default settings are uniform
        provides a uniform logging format
    """
    loggers = {}
    logger  = None
    formatter = None
    log_level = None
    file_handler = None
    config = {
        'SPOOL_DIR': '/var/spool/docket',   # overridden by environment
        'SECRET_KEY': 'CHANGE_THIS',        # overridden by environment
        'SESSION_COOKIE_NAME': 'DOCKET_COOKIE',
        'USE_X_SENDFILE': False,
        #'CELERY_URL': 'redis://localhost:6379', # If not provided we should error out
        'CELERY_TASK_IGNORE_RESULT': True,
        'LOG_MSG_FORMAT': '[%(processName)-8s] %(message)s',
        'LOG_DATE_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
        'LOG_DATE_UTC': True,
        'LOG_LEVEL': 'info',
        'LOG_FILE_BACKUPS' : 7,
        'LOG_FILE_MSG_FORMAT': '%(asctime)s[%(processName)-8s] %(message)s',
        'LOG_FILE_DATE_FORMAT': '%Y%jT%H:%M:%S',
        'LOG_FILE_LEVEL': 'info',
        'STENOGRAPHER_INSTANCES': { 'host': '127.0.0.1', 'sensor': 'sensor-1', 'port': 1234, 'key': '/etc/stenographer/certs/client_key.pem', 'cert': '/etc/stenographer/certs/client_cert.pem', 'ca': '/etc/stenographer/certs/ca_cert.pem' },
        'DOCKET_NO_REDIS': False,
        'WEB_ROOT': '/api',
        'PCAP_WEB_ROOT': '/results'
    }
    _default = config.copy()
    _redis = None

    @classmethod
    def load(cls, filename=None, flask_app=None, logger=None, env=None):
        """ Set Config from a yaml file:
            filename a config file: search for the file in several directories
        """

        import itertools
        app_root = flask_app.root_path if flask_app else '/opt/docket/docket'
        fs_root  = os.path.abspath(os.sep)
        paths = itertools.product(
            ( filename,                     # filename.yaml
             'docket',                      # docket.yaml
            ),
            [ tuple(),                      # <empty> - filename can be any valid path
             (fs_root, 'etc', 'docket'),    # /etc/docket/filename
             (fs_root, 'etc',),             # /etc/filename
            ]
        )
        for f, p in paths:
            if not f:
                continue
            filepath = os.path.join(*(p + (f,)))
            filepath = os.path.expanduser(filepath)
            if os.path.isfile(filepath):
                break
            elif os.path.isfile(filepath+'.yaml'):
                filepath += '.yaml'
                break
            print("Config: >{}< not found".format(filepath))

        # load the config file and update our class config data
        if filepath:
            with open(filepath) as f:
                cls.config.update(yaml.load(f.read()))
                print("Config: loaded >{}<".format(filepath))

        if type(env) is dict:
            cls.config.update(env)

        # I'm having the hardest time getting logging to 'work'
        # TODO have exceptions output in LOG_FILE... (WHY NOT)
        cls.loggers['docket'] = logging.getLogger(
            Config.get('LOGGER_NAME', 'docket'))

        # Add streamhandler as default
        _logger = cls.loggers['docket']
        _console = logging.StreamHandler(sys.stdout)
        _console.setLevel(log_level(cls.config['LOG_LEVEL']))
        _console.setFormatter(
            logging.Formatter(fmt=cls.config['LOG_MSG_FORMAT'],
                              datefmt=cls.config['LOG_DATE_FORMAT'])
        )
        _logger.addHandler(_console)

        cls.loggers[None] = logging.getLogger()
        if isinstance(logger, logging.Logger):
            cls.loggers['docket'] = logger
        if flask_app:
            flask_app.config.from_mapping(cls.config)
            cls.loggers['flask'] = flask_app.logger

        cls._setup_loggers()

        return cls.config

    @classmethod
    def _setup_loggers(cls):
        cls.log_level = log_level(cls.config['LOG_LEVEL'])
        cls.formatter = logging.Formatter(
                            fmt=cls.config['LOG_MSG_FORMAT'],
                            datefmt=cls.config['LOG_DATE_FORMAT'])

        handler = None
        handler = None
        if not cls.file_handler and cls.get('LOG_FILE', None):
            from logging.handlers import TimedRotatingFileHandler
            handler = TimedRotatingFileHandler(
                cls.config['LOG_FILE'],
                when='midnight',
                backupCount=cls.config['LOG_FILE_BACKUPS'],
                utc=cls.config['LOG_DATE_UTC']
            )
            file_fmt = logging.Formatter(
                            fmt=cls.config['LOG_FILE_MSG_FORMAT'],
                            datefmt=cls.config['LOG_FILE_DATE_FORMAT'])
            handler.setLevel(log_level(cls.config['LOG_FILE_LEVEL']))
            handler.setFormatter(file_fmt)
            cls.file_handler = handler
            logging.info("Logging to {}:{}".format(
                cls.config['LOG_FILE'], cls.config['LOG_FILE_LEVEL']))

        for l in cls.loggers.values():
            l.setLevel(cls.log_level)
            for h in l.handlers:
                if not isinstance(h, logging.FileHandler):
                    h.setFormatter(cls.formatter)
            if handler:
                l.addHandler(handler)

        cls.get_logger()

    @classmethod
    def redis(cls):
        if cls._redis:
            return cls._redis
        if cls.get('DOCKET_NO_REDIS') or not cls.get('REDIS_URL'):
            return None
        cls._redis = redis.from_url(url=cls.get('REDIS_URL'))
        return cls._redis

    @classmethod
    def get_logger(cls, name=None):
        cls.logger = cls.loggers.get(name or cls.get('LOGGER_NAME'), cls.loggers['docket'])
        return cls.logger

    @classmethod
    def _set(cls, key, default, minval=None):
        """ _set checks for consistent 'default' values and enforces minimum value """
        old = cls._default.get(key)
        if old is not None and old != default:  # find programmers providing conflicting defaults
            raise ValueError("Config [{}] - disagreement in defaults: {}:{}".format(key, old, default))
        if type(minval) in (int, float):
            if default < minval:
                raise ValueError("Config [{}] - default < minval: {}:{}".format(key, default, minval))
        cls._default[key] = default
        if not key in cls.config:
            cls.config[key] = default
        elif type(minval) in (int, float):
            cls.config[key] = max(minval, cls.config[key])

    @classmethod
    def setdefault(cls, key, default, minval=None):
        cls._set(key, default, minval)
        return cls.config[key]

    @classmethod
    def get(cls, key, default=None, minval=None):
        if default is not None:
            return cls.setdefault(key, default, minval)
        if type(minval) in (int, float):
            cls.config[key] = max(cls.config.get(key), minval)
        return cls.config.get(key)
