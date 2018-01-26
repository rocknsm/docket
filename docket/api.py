from flask import Flask, Blueprint, Response
from flask_restful import Api

from resources.query import QueryRequest, ApiRequest, RawRequest

from config import Config

# Declare the blueprint
api_bp = Blueprint('query', __name__)
api = Api(api_bp)

# Add resources
# consider 'login_required' for queries

# RawRequest handles valid stenographer queries
#   Get /raw/host+1.2.3.4+and+port+80
#   POST /query -d 'host 1.2.3.4 and port 80'
api.add_resource(RawRequest,
                 '/raw/<query>/',               # GET  /raw/host+1.2.3.4+port+80
                 '/query/',                     # POST /query -d 'host 1.2.3.4 port 21'
                )

# QueryRequest handles encoded queries
#   GET /uri/name/value
#   POST / Json or HTML Forms
api.add_resource(QueryRequest,
                 '/uri/<path:path>/',           # GET  /uri/host/1.2.3.4/port/80
                 '/',                           # POST / -d '{ "port":21, "after-ago":"1m" }'
                )

# ApiRequest handles metadata requests
#   GET /urls   GET /urls/d6c1e79adf9f46bf6187fd92fff016e5,734d929c61e64315b140cb7040115a70
#   GET /ids    GET /ids/734d929c61e64315b140cb7040115a70,7065d7548b8e717b5bdac1d074e80b55
#   GET /status GET /status/734d929c61e64315b140cb7040115a70,7065d7548b8e717b5bdac1d074e80b55
#   GET /stats  GET /stats/sensor.1,sensor.2
api.add_resource(ApiRequest,
                 '/<api>/<path:selected>/',
                 '/<api>/',
                )
