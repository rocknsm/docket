#!/usr/bin/env python
from docket import app, celery
import os

manager = app.manager()

@manager.command
def list_routes():
    import urllib
    output = []
    _app = app.flask_app
    for rule in _app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        line = urllib.unquote('{:30s} {:25s} {}'.format(rule.endpoint, methods, rule))
        output.append(line)

    for line in sorted(output):
        print line

@manager.command
def dump_config():
    import pprint
    _app = app.flask_app
    _config = {}
    _config.update(_app.config)
    class MyDefault:
        def default(self, value):
            return "<VALUE>"

    pp = pprint.PrettyPrinter()
    pp.pprint(_config)

if __name__ == '__main__':
    manager.run()
