from flask import Flask, Blueprint
from flask_restful import Resource, Api

app = Flask(__name__)
api_bp = Blueprint('api', __name__)
app.register_blueprint(api_bp)
api = Api(api_bp)

class Host(Resource):
    def get(self, addr):
        # Setup things here for getting file handle
        def generate():
            for block in _sock:
                yield block
        return Response(generate(), mimetype='application/vnd.tcpdump.pcap')

api.add_resource(Host, '/host/<string:addr>')

class StenoStats(Resource):
    def get(self):
        return {'foo': 'bar'}

api.add_resource(StenoStats, '/')

if __name__ == '__main__':
    app.run(debug=True)
