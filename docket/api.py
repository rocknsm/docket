from flask import Flask, Blueprint, Response
from flask_restful import Resource, Api

app = Flask(__name__)
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

class SingleHost(Resource):
    def get(self, addr):
        # Setup things here for getting file handle
        _sock = ['foo', 'bar', 'baz', 'bazzle', 'razzle', 'dazzle', addr]
        def generate():
            for block in _sock:
                yield block + ","
        return Response(generate(), mimetype='application/vnd.tcpdump.pcap')

api.add_resource(SingleHost, '/host/<string:addr>')

class DoubleHost(Resource):
    def get(self, addr1, addr2):
        data = "host"
class StenoStats(Resource):
    def get(self):
        return {'foo': 'bar'}

api.add_resource(StenoStats, '/stats/')

if __name__ == '__main__':
    app.register_blueprint(api_bp)
    app.run(debug=True)
