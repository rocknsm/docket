from __future__ import print_function
# A central location for the config dictionary
#   see application for initialization
import yaml
import os
import logging

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
        'WEB_ROOT': '/',
        'SPOOL_DIR': '/var/spool/docket',   # overridden by environment
        'SECRET_KEY': 'CHANGE_THIS',        # overridden by environment
        'CELERY_TASK_IGNORE_RESULT': True,
        'LOG_MSG_FORMAT': '[%(processName)-8s] %(message)s',
        'LOG_DATE_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
        'LOG_DATE_UTC': True,
        'LOG_LEVEL': 'info',
        'LOG_FILE_BACKUPS' : 7,
        'LOG_FILE_MSG_FORMAT': '%(asctime)s[%(processName)-8s] %(message)s',
        'LOG_FILE_DATE_FORMAT': '%Y%jT%H:%M:%S',
        'LOG_FILE_LEVEL': 'info',
    }
    _default = config.copy()

    @classmethod
    def load(cls, filename=None, flask_app=None, logger=None):
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
#            (os.curdir, os.pardir, 'conf'),# CWD/../conf/filename
             (app_root, 'conf'),            # APP/conf/filename
             ('conf',)]                     # ./conf/filename
        )
        for f,p in paths:
            if not f:
                continue
            filepath = os.path.join(*(p + (f,)) )
            filepath = os.path.expanduser(filepath)
            if os.path.isfile(filepath):
                break
            elif os.path.isfile(filepath+'.yaml'):
                filepath += '.yaml'
                break
            print("Config: >{}< not found".format(filepath))

        # load the config file and update our class config data
        with open(filepath) as f:
            cls.config.update(yaml.load(f.read()))
        print("Config: loaded >{}<".format(filepath))

        # I'm having the hardest time getting a logging to work
        cls.loggers['docket']= logging.getLogger(Config.get('LOGGER_NAME','docket'))
        if isinstance(logger, logging.Logger):
            cls.loggers[None] = logger
        if flask_app:
            flask_app.config.from_mapping(cls.config)
            cls.loggers['flask'] = flask_app.logger
            #cls.config = flask_app.config

        cls._setup_loggers()

        return cls.config

    @classmethod
    def _setup_loggers(cls):
        cls.log_level = log_level(cls.config['LOG_LEVEL'])
        cls.formatter = logging.Formatter(fmt=cls.config['LOG_MSG_FORMAT'],
                                          datefmt=cls.config['LOG_DATE_FORMAT'])

        handler = None
        if not cls.file_handler and cls.get('LOG_FILE', None):
            from logging.handlers import TimedRotatingFileHandler
            handler = TimedRotatingFileHandler(
                cls.config['LOG_FILE'],
                when='midnight',
                backupCount=cls.config['LOG_FILE_BACKUPS'],
                utc=cls.config['LOG_DATE_UTC']
            )
            file_fmt = logging.Formatter(fmt=cls.config['LOG_FILE_MSG_FORMAT'],
                                         datefmt=cls.config['LOG_FILE_DATE_FORMAT'])
            handler.setLevel(log_level(cls.config['LOG_FILE_LEVEL']))
            handler.setFormatter(file_fmt)
            cls.file_handler = handler
            logging.info("Logging to {}:{}".format(cls.config['LOG_FILE'], cls.config['LOG_FILE_LEVEL']))

        for l in cls.loggers.values():
            l.setLevel(cls.log_level)
            for h in l.handlers:
                if not isinstance(h, logging.FileHandler):
                    h.setFormatter(cls.formatter)
            if handler:
                l.addHandler(handler)

        cls.get_logger()


    @classmethod
    def get_logger(cls, name=None):
        cls.logger = cls.loggers.get(name or cls.get('LOGGER_NAME'), cls.loggers['docket'])
        return cls.logger

    @classmethod
    def _set(cls, key, default):
        """ _set checks for consistent use of 'default' config values """
        old = cls._default.get(key)
        if old is not None and old != default:  # find programmers providing conflicting defaults
            raise Exception("Config [{}] - disagreement in defaults: {}:{}".format(key, old, default))
        cls._default[key] = default
        return cls.config.setdefault(key, default)

    @classmethod
    def setdefault(cls, key, default, min=None):
        rv = cls._set(key, default)
        if min and rv < min:
            cls.config[key] = min
            rv = min
        return rv

    @classmethod
    def get(cls, key, default=None):
        if default is not None:
            return cls._set(key, default)
        return cls.config.get(key)
