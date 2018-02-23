##
## Copyright (c) 2017, 2018 RockNSM.
##
## This file is part of RockNSM
## (see http://rocknsm.io).
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
##
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
#   GET /raw/host+1.2.3.4+and+port+80
#   POST /query -d 'host 1.2.3.4 and port 80'
# api.add_resource(RawRequest,
#                  '/raw/<query>/',
#                  '/query/',
#                 )
api.add_resource(RawRequest, '/raw/<query>', endpoint="query.rawrequest.get", methods=['GET']) # GET  /raw/host+1.2.3.4+port+80
api.add_resource(RawRequest, '/query/', endpoint="query.rawrequest.post", methods=['POST']) # POST /query -d 'host 1.2.3.4 port 21'

# QueryRequest handles encoded queries
#   GET /uri/name/value
#   POST / Json or HTML Forms
# api.add_resource(QueryRequest,
#                  '/uri/<path:path>/',
#                  '/',
#                 )
api.add_resource(QueryRequest, '/', endpoint="query.queryrequest.post", methods=['POST'])  # POST / -d '{ "port":21, "after-ago":"1m" }'
api.add_resource(QueryRequest, '/uri/<path:path>', endpoint="query.queryrequest.get", methods=['GET'])  # GET  /uri/host/1.2.3.4/port/80

# ApiRequest handles metadata requests
#   GET /urls   GET /urls/d6c1e79adf9f46bf6187fd92fff016e5,734d929c61e64315b140cb7040115a70
#   GET /ids    GET /ids/734d929c61e64315b140cb7040115a70,7065d7548b8e717b5bdac1d074e80b55
#   GET /status GET /status/734d929c61e64315b140cb7040115a70,7065d7548b8e717b5bdac1d074e80b55
#   GET /stats  GET /stats/sensor.1,sensor.2
api.add_resource(ApiRequest,
                 '/<api>/<path:selected>/',
                 '/<api>/', methods=['GET']
                )
