from flask_restful import Resource
from flask import Response, jsonify

class Stats(Resource):
    def get(self, sensors=None):
        from tasks import get_stats

        result = get_stats.apply_async()
        while not result.ready():
            pass

        if result.successfull():
            return jsonify(result.result)
        else:
            response = jsonify({'error': 'An unknown error occurred.'})
            response.status_code = 500
            return response

    def post(self):
        pass


