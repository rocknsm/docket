from flask import Flask, Blueprint, Response
from flask_restful import Api

from resources.query import QueryRequest, ApiRequest, RawRequest

from config import Config

# Declare the blueprint
api_bp = Blueprint('api', __name__)
api    = Api(api_bp)

# Add resources
WEB_ROOT = Config.get('WEB_ROOT', '/')
# consider 'login_required' for queries
api.add_resource(RawRequest, WEB_ROOT+'raw/<string:query>' )     # ex: /raw/host+1.2.3.4+port+80
api.add_resource(QueryRequest,
        WEB_ROOT+'q/<path:path>',                   # ex: GET  /q/host/1.2.3.4/port/80
        WEB_ROOT,                                   # ex: POST / -d '{ "port":21, "after-ago":"1m" }'
        )
api.add_resource(ApiRequest,
        WEB_ROOT+'<string:api>/<path:selected>',    # ex: GET /urls/ID,ID,...
        WEB_ROOT+'<string:api>',
        )

#if __name__ == '__main__':
#    app = Flask(__name__)
#    app.register_blueprint(api_bp)
#    app.run(debug=True)
