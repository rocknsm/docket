from flask import Flask, Blueprint, Response
from flask_restful import Resource, Api

from resources.pcap import PcapApi, PcapUri, RawQuery
from resources.stats import Stats

# Declare the blueprint
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

# Add resources
api.add_resource(PcapApi, '/api/')
api.add_resource(PcapUri, '/pcap/<path:path>')
api.add_resource(RawQuery, '/query' )
api.add_resource(Stats, '/stats/', '/stats/<string:sensors>', endpoint='stats')

if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    app.run(debug=True)
