from flask_restful import Resource
from flask import Response, jsonify


class Stats(Resource):
    def get(self, sensors=None):
        from tasks import get_stats

        result = get_stats()
        return jsonify(result)

    def post(self):
        pass


