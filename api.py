from flask import Flask, Blueprint, Response
from flask_restful import Resource, Api

from resources.stats import Stats

app = Flask(__name__)
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

class StenoPcap(Resource):
    def get(self, path):
        pass

    def post(self):
        pass

api.add_resource(StenoPcap, '/pcap/<path:path>', defaults={'path': ''} )

api.add_resource(Stats, '/stats/', '/stats/<string:sensors>', endpoint='stats')

if __name__ == '__main__':
    app.register_blueprint(api_bp)
    app.run(debug=True)
