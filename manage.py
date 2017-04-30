from flask import Flask
from flask.ext.script import Manager
from docket.api import api_bp

app = Flask(__name__)
app.config['APP_CONFIG'] = 'conf/docket.yaml'
app.register_blueprint(api_bp)

manager = Manager(app)

if __name__ == '__main__':
    manager.run()
