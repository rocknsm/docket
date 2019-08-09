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
# Query - A Class for tracking queries through the process and interfacing with them
# QueryRequest - implements Flask Restful to fill requests with formatted data
from collections import namedtuple
from datetime import datetime, timedelta
import re
import os

from werkzeug.exceptions import BadRequest
from flask import jsonify, request, render_template, Response, make_response
from flask_restful import Resource, inputs, reqparse
from json import dumps
import yaml
import redis

from common.utils import parse_duration, parse_capacity, file_modified, ISOFORMAT \
        , recurse_update, md5, validate_ip, validate_net, readdir, spool_space \
        , epoch, from_epoch, write_yaml, update_yaml, space_low, is_str, is_sequence
from config import Config

RequestInfo = namedtuple('RequestInfo', ['ip', 'port', 'agent'])
Event = namedtuple('Event', ['datetime', 'name', 'msg', 'state'])
Result = namedtuple('Result', ['datetime', 'name', 'msg', 'state', 'value'])

_REDIS_PREFIX = 'Docket.Query.'
_DATE_FORMAT = Config.get('DATE_FORMAT', "%Y-%m-%dT%H:%M:%S")
_INSTANCES = Config.get('STENOGRAPHER_INSTANCES')
_SENSORS = []

for steno in _INSTANCES:
    steno['stats'] = {}
    _SENSORS.append(steno['sensor'])

Config.setdefault('TIME_WINDOW', 60, minval=1)


def enforce_time_window(time):
    """ given a datetime, return the start time of it's TIME_WINDOW
        aka - 'round down' a time into our TIME_WINDOW
    """
    if not Config.get('TIME_WINDOW'):
        return time
    return from_epoch(epoch(time)
                      // Config.get('TIME_WINDOW')
                      * Config.get('TIME_WINDOW'))


def _get_request_nfo():
    """ grab client info for logging, etc..
        getting this information might depend on the stack,
        This function is designed for nginx
    """
    return RequestInfo(ip = request.environ.get('REMOTE_ADDR', request.remote_addr),
                       port = request.environ.get('REMOTE_PORT', '_UNKNOWN_'),
                       agent= request.environ.get('HTTP_USER_AGENT', '_UNKNOWN_')
                      )


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    from datetime import datetime, date

    if isinstance(obj, (datetime, date)):
        return obj.strftime(_DATE_FORMAT)[:-3]
    raise TypeError("Type %s not serializable" % type(obj))


class Query:
    """ Query               handles metadata and actions to process docket queries:
        q = Query(f)        creates a query from a dict of fields
        l = Query(idstr)    creates a query by loading the query file in SPOOL_DIR/idstr (standard location)
        t = Query(tuple)    creates a query from tuple created by .tupify()
        q.enqueue()         send the query to celery to start processing.

        Query(f).enqueue()  shorthand
    """
    Tuple = namedtuple('QueryTuple', ['query', 'time'] )

    LONG_AGO = -1 * abs(parse_duration(Config.get('LONG_AGO', '24h')))

    WEIGHTS = {
        'enabled': (bool(Config.get('WEIGHT_TOTAL')) and
                    bool(Config.get('WEIGHT_THRESHOLD')) and
                    bool(Config.get('WEIGHT_HOURS'))),
        'total': parse_capacity(Config.get('WEIGHT_TOTAL')),
        'limit': parse_capacity(Config.get('WEIGHT_THRESHOLD')),
        'port' : Config.get('WEIGHT_PORTS', 100.0),
        'hour': Config.get('WEIGHT_HOURS'),
        'net' : Config.get('WEIGHT_NETS', 2.0),
        'ip' : Config.get('WEIGHT_IPS', 50.0),
    }


    # TIME_RX = re.compile(r'after (?P<after>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) and before (?P<before>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)')
    EMPTY_THRESHOLD = parse_capacity(Config.get('EMPTY_THRESHOLD', '25B'))
    # Query.events can have a 'state': states are used to filter events for display
    RECEIVING = 'Requesting'
    RECEIVED = 'Request Complete'
    EMPTY = 'Completed. no packets returned'
    FINISHED = 'Finished'
    CREATED = 'Created'
    SUCCESS = 'Completed'
    MERGE = 'Merging'
    ERROR = 'Error'
    FAIL = 'Failed'
    FINAL_STATES = (
        FAIL,
        SUCCESS,
    )

    def __init__(self, fields=None, qt=None, q_id=None, query=None):
        self.query = None           # string: query formatted for stenoapi
        self.state = None           # string: one of (RECEIVING, RECEIVED, MERGE, SUCCESS, ERROR, FAIL)
        self._id = None             # a hash of the normalized query string, uniquely identifies this query to prevent duplicates
        self.events = []            # a sorted list of events including errors... TODO FIX ME

        if qt:
            self._detupify(qt)

        if q_id and is_str(q_id) and len(q_id) >= 32:
            self.load(q_id=q_id)

        if query and is_str(query):
            self.query = query

        if fields and isinstance(fields, dict):
            self._build_query(fields)

    def load(self, path=None, q_id=None, from_file=False):
        """ query data, if no path is provided use the default (requires id)
            path - ignore redis and read the file from the given path
            from_file - ignore redis and read the file from disk
        """
        if path is not None:
            if os.path.exists(path):
                return update_yaml(path, self) != False
            self.error('load', "No Such path {}".format(path))
            return False
        elif Config.redis() and not from_file:
            r = Config.redis()
            key = _REDIS_PREFIX + (q_id or self.id)
            old = r.get(key)
            if old:
                old = yaml.load(old)
                self.update(old)
                return True
        q_id = q_id or self.id
        if q_id:
            return update_yaml(Query.yaml_path_for_id(q_id), self) != False
        raise Exception("Can't load a Query without an ID: {}".format(self))

    def save(self, path=None, q_id=None, to_file=False):
        """ save this query to the default location, clobbering old values
            path - write the query to the given file path and return True if successful. Overrides other keyargs
            to_file - ensure the file on disk is written, will also write to redis if configured
        """
        Config.logger.info("Query Save state:{}, Last Event:{}".format(self.state, self.events[-1]))
        if path is not None:
            if os.path.exists(path):
                return write_yaml(path, self)
            self.error('load', "No Such path {}".format(path))
            return False
        if Config.redis():
            r = Config.redis()
            key = _REDIS_PREFIX + self.id
            r.set(key, yaml.dump(self))
            if not to_file:
                return True
        q_id = q_id or self.id
        if q_id:
            return write_yaml(Query.yaml_path_for_id(q_id), self)
        Exception("Can't save Query {}".format(self))

    def update(self, other):
        """ update self from other's data,
            other can be a Query, dict, or yaml string.
        """
        Config.logger.debug("updating: {} with {}".format(self, other))
        if type(other) is dict and other:
            Config.logger.debug("Dict update: {} with {}".format(self, other))
            recurse_update(self.__dict__, other, ignore_none=True)
            self._fix_events()
            return True
        elif isinstance(other, Query):
            Config.logger.debug("instance update: {} with {}".format(self, other))
            recurse_update(self.__dict__, other.__dict__, ignore_none=True)
            self._fix_events()
            return True
        elif type(other) is str:
            return self.update(yaml.load(other))
        return False

    def tupify(self):       # We can't queue an object. This is all the data we need to use queue in the celery worker
        """ Serializes the basic values used to define a query into a tuple """
        return Query.Tuple(self.query, self.queried.strftime(ISOFORMAT))

    def _detupify(self, query_tuple):
        query_tuple = Query.Tuple(*query_tuple)        # namedTuples lose their names when serialized
        self.query = query_tuple.query
        self.events = [Event(datetime=datetime.strptime(query_tuple.time, ISOFORMAT), name=Query.CREATED, msg=None, state=Query.CREATED)]
        self._fix_events()

    def _fix_events(self):
        """ resort events, the list order can be wrong when loaded from a file """
        self.events.sort()

    @property
    def id(self):
        """ hexdigest of the query - uniquely identifies the request based on the query string (assumes query times are absolute) """
        if self._id is not None:
            return self._id
        elif self.query:
            # calculate a 'query' hash to be our id
            self._id = md5(self.query)
            if Config.get('UUID_FORMAT'):
                self._id = '-'.join((self._id[:8], self._id[8:12], self._id[12:16], self._id[16:20], self._id[20:]))
            return self._id

    @property
    def queried(self):
        """ shortcut for 'when a user submitted this query' """
        if not self.events:
            self.progress(Query.CREATED, state=Query.CREATED)
        return self.events[0].datetime

    @property
    def query_time(self):
        """ force 'queried' into a TIME_WINDOW for use in a query string """
        return enforce_time_window(self.queried)

    def __str__(self):
        return "[{}]".format( self.id if self.query else "partial QUERY" )

    def time_requested(self):
        """ returns an ISO date (ordinal) - when the query was requested """
        return self.queried.strftime(_DATE_FORMAT)[:-3]

    @property
    def yaml_path(self):
        return Query.yaml_path_for_id(self.id)

    @classmethod
    def yaml_path_for_id(cls, q_id):
        """  path used to record this query as yaml """
        return cls.job_path_for_id(q_id, Config.get('QUERY_FILE', 'query') + '.yaml')

    def path(self, path):
        return self.job_path_for_id(self._id, path)

    @property
    def job_path(self):
        """ path for this query's artifacts """
        return self.job_path_for_id(self._id)

    @staticmethod
    def job_path_for_id(q_id, path=None):  # ensure canonical naming - everything uses this function
        parts = (Config.get('SPOOL_DIR'), q_id)
        if path:
            parts += (path,) if is_str(path) else path
        return os.path.join(*parts)

    @property
    def invalid(self):
        """ checks if this query is valid, and returns a dict of things that are wrong """
        if self.query is None:
            self.error("invalid", "No query string")
        if self.id is None:
            self.error("invalid", "No Id ")
        if not self.events:
            self.error("invalid", "No request time")
        return self.errors

    @property
    def errors(self):
        """ returns a dictionary of errors recorded about this query """
        return [ e for e in self.events if e.state in (Query.ERROR, Query.FAIL) ]

    def error(self, name, msg, status=None):
        """ adds an error event to the query ie: error('stenographer', "Bad Request" )
            if LOG_LEVEL is 'debug', add the caller's name and line number
        """
        if Config.get("DEBUG"):
            from inspect import getframeinfo, stack
            caller = getframeinfo(stack()[1][0])
            msg = "{}:{} - {}".format(caller.filename, caller.lineno, msg)
            del caller      # This delete is redundant, but a stack frame contains multitudes: we _must not_ keep it around
        self.progress(name, msg, status or Query.ERROR)

    def info(self, msg):
        Config.logger.info("Query: " + msg)

    def _build_query(self, fields):
        Config.logger.debug("_build_query {}".format(str(fields)))

        q_fields = {'host': [],
                    'net' : [],
                    'port': [],
                    'proto' : None,
                    'proto-name' : None,
                    'after-ago'  : None,
                    'before-ago' : None,
                    'after' : None,
                    'before' : None,
                   }
        q_fields.update(fields)
        self.progress(Query.CREATED, state=Query.CREATED)

        start = self.query_time + self.LONG_AGO
        end   = self.query_time + timedelta(minutes=1)

        qry_str = []
        weights = {'ip': 0,
                   'net': 0,
                   'port': 0}
        for host in sorted(q_fields['host']):
            Config.logger.debug("Parsing host: %s", host)
            if len(host) == 0:
                continue

            validate_ip(host)
            qry_str.append('host {}'.format(host))
            weights['ip'] += 1
        for net in sorted(q_fields['net']):
            Config.logger.debug("Parsing net: %s", net)
            if len(net) == 0:
                continue

            validate_net(net)
            qry_str.append('net {}'.format(net))
            weights['net'] += 1
        for port in sorted(q_fields['port']):
            Config.logger.debug("Parsing port: %s", port)
            try:
                if 0 < int(port) < 2**16:
                    qry_str.append('port {}'.format(int(port)))
                    weights['port'] += 1
                else:
                    raise ValueError()
            except ValueError:
                raise BadRequest("Port {} out of range: 1-65535".format(port))
        if q_fields['proto']:
            try:
                if 0 < int(q_fields['proto']) < 2**8:
                    qry_str.append('ip proto {}'.format(q_fields['proto']))
                else:
                    raise ValueError()
            except ValueError:
                raise BadRequest("protocol number {} out of range 1-255".format(q_fields['proto']))
        if q_fields['proto-name']:
            if q_fields['proto-name'].upper() not in ['TCP', 'UDP', 'ICMP']:
                raise BadRequest(description="Bad proto-name: {}".format(q_fields['proto-name']))
            qry_str.append(q_fields['proto-name'].lower())
        if q_fields['after-ago']:
            dur = parse_duration(q_fields['after-ago'])
            if not dur:
                raise BadRequest("can't parse duration: {}".format(q_fields['after-ago']))
            start = enforce_time_window(self.query_time - dur)
        if q_fields['before-ago']:
            dur = parse_duration(q_fields['before-ago'])
            if not dur:
                raise BadRequest("can't parse duration: {}".format(q_fields['before-ago']))
            end = enforce_time_window(self.query_time - dur)
        if q_fields['after']:
            print "Processing 'after': {}".format(q_fields['after'])
            dur = parse_duration(q_fields['after'])
            print "Duration {}".format(dur)
            if dur:
                start = enforce_time_window(self.query_time - dur)
                print "Start w/ duration: {}".format(start)
            else:
                start = enforce_time_window(inputs.datetime_from_iso8601(q_fields['after']).replace(tzinfo=None))
                print "Start w/o duration: {}".format(start)

        if q_fields['before']:
            dur = parse_duration(q_fields['before'])
            if dur:
                end = enforce_time_window(self.query_time - dur)
            else:
                end = enforce_time_window(inputs.datetime_from_iso8601(q_fields['before']).replace(tzinfo=None))
            end += timedelta(seconds=Config.get('TIME_WINDOW'))

        # Check the request's 'weight'
        if Query.WEIGHTS['enabled'] and not q_fields.get('ignore-weight'):
            req_weight = ( Query.WEIGHTS['total']
                          * ((end-start).total_seconds() / (Query.WEIGHTS['hour'] * 3600) )
                          / (sum((val * Query.WEIGHTS[k] for k, val in weights.items())) or 1)
                         )
            if req_weight > Query.WEIGHTS['limit']:
                self.error('build_query',
                           "Request is too heavy: {}/{}:\t{}".format(req_weight,
                                                                     Query.WEIGHTS['limit'],
                                                                     jsonify(q_fields)))
                raise BadRequest("Request parameters exceed weight: %d/%d" %(req_weight, Query.WEIGHTS['limit']))

        # Stenographer issue 132 Query buffer of 2 minutes
        start += timedelta(seconds=-120)
        end += timedelta(seconds=120)

        qry_str.append('after {}'.format(start.strftime(ISOFORMAT)))
        qry_str.append('before {}'.format(end.strftime(ISOFORMAT)))

        self.query = " and ".join(qry_str)
        if not self.query:
            Config.logger.info("Bad request: {}".format(jsonify(q_fields)))
            return None

        Config.logger.debug("build_query: <{}>".format(self.query))

        # if we want to support limiting the query, it would require rethinking our duplicate detection
        #if q_fields['sensors']:
        #    self.sensors = q_fields['sensors']
        return self.id

    @classmethod
    def find(cls, fields):
        r = Config.redis()
        if not r:
            return []
        results = []
        ids = Query.get_unexpired()
        for i in ids:
            q = Query(q_id=i)
            if not q.query:
                # sometimes query meta data is incomplete, usually when I'm break^H^H^H^H^Htesting.
                continue
            for k,v in fields.items():
                if k in ('after-ago', 'after', 'before-ago', 'before'):
                    dur = parse_duration(v)
                    if dur:
                        v = (datetime.utcnow() - dur)
                    else:
                        v = inputs.datetime_from_iso8601(v)
                        pass
                    if (q.queried < v) and k in ('after-ago', 'after'):
                        q = None
                        break
                    elif (q.queried > v) and k in ('before-ago', 'before'):
                        q = None
                        break
                    pass
                elif k in ('sensors', 'limit-packets', 'limit-bytes'):
                    continue
                elif k not in q.query:
                    Config.logger.info("Skipping: {} - {}".format(q.query, k))
                    q = None
                    break
                else:
                    if is_sequence(v) and v != [vi for vi in v if q.query.find(vi) >= 0]:
                        Config.logger.info("Skipping: {} - {}".format(q.query, v))
                        q = None
                        break
                    elif is_str(v) and v not in q.query:
                        Config.logger.info("Skipping: {} - {}".format(q.query, v))
                        q = None
                        break
            if q:
                results.append(q.json())
        return results

    @staticmethod
    def thead():
        col = lambda k, s, t: {"key": k, "str": s, "type": t}
        columns = [
            col("state", "State", "string"),
            col("time", "Time requested", "string"),
            col("id", "ID", "id"),
            col("url", "Pcap URL", "url"),
            col("query", "Query", "string"),
        ]
        return columns

    def json(self):
        return { 'id': self.id,
                 'state': self.state,
                 'query': self.query,
                 'url': self.pcap_url,
                 'time' : self.time_requested(),
                 'query': self.query}

    def enqueue(self):
        """ queue this query in celery for fulfillment """
        if self.invalid:
            raise Exception("Invalid Query " + self.errors)
        from tasks import query_task
        query_task.apply_async(queue='query', kwargs={'query_tuple' :self.tupify()})
        return self.json()

    @property
    def pcap_url(self):
        return self.pcap_url_for_id(self.id)

    @staticmethod
    def pcap_url_for_id(id):
        return "{}/{}/{}.pcap".format(Config.get('PCAP_WEB_ROOT', '/results'), id, Config.get('MERGED_NAME'))

    @property
    def pcap_path(self):
        return Query.pcap_path_for_id(self.id)

    @staticmethod
    def pcap_path_for_id(q_id):
        if q_id:
            return os.path.join(Config.get('SPOOL_DIR'), q_id, '%s.pcap' % Config.get('MERGED_NAME'))

    def complete(self, state=SUCCESS):
        """ why a separate method: because someone will definitely want to check for the 'completed' status so it better be reliably named """
        if state not in Query.FINAL_STATES:
            raise ValueError("query.complete() requires a 'FINAL_STATE'")
        self.progress(Query.FINISHED, state=state)

    def progress(self, name, msg=None, state=None):
        """ Record the time 'action' occurred """
        e = Event(datetime.utcnow(), name, msg, state)
        self.events.append(e)

        if self.state not in Query.FINAL_STATES:
            self.state = state if state is not None else self.state

        if state in (Query.ERROR, Query.FAIL):
            Config.logger.warning("Query[{}] Error: {}:{}".format(self.id, name, msg or ''))
        else:
            Config.logger.info("Query[{}] {}:{}:{}".format(self.id, name, msg or '', state))
        return e

    def result(self, name, msg=None, state=None, value=None):
        """ Record the result of a stenographer query """
        result = Result(datetime=datetime.utcnow(), name=name, msg=msg, state=state, value=value)
        self.events.append(result)
        Config.logger.info("Query[{}] {}:{}".format(self.id, name, msg or ''))
        return result

    @property
    def successes(self):
        """ a list of successful query results """
        return [ e for e in self.events if type(e) is Result and e.state == Query.RECEIVED ]

    @staticmethod
    def get_unexpired(ids=None):
        """ return a list of query IDs that are still available on the drive
            the queries can be in various states of processing
        """
        return [
            f for f in readdir(Config.get('SPOOL_DIR'))
            if (f not in ['.', '..']) and
            (not ids or f in ids) and
            (len(f) >= 32)
        ]

    def status(self, full=False):
        """ describe this query's state in detail """
        if self.events:
            status = {
                'state': self.state,
                'requests': {
                    r.name: r._asdict()
                    for r in self.events
                    if type(r) is Result
                },
                'events': [
                    e._asdict()
                    for e in self.events
                    if full or e.state
                ],
                'successes': [
                    e._asdict()
                    for e in self.successes
                ],
            }
            return status
        return {'state': self.state}

    @staticmethod
    def status_for_ids(ids):
        """ return a dictionary of id : {status} """
        if type(ids) is str:
            ids = list(ids)
        return { i: Query(q_id=i).status(full=True) for i in ids }

    @staticmethod
    def expire_now(ids=None):
        """ Deletes queries with supplied ids.
            Returns a list of ids that couldn't be deleted.
            Ignore non-existent entries
        """
        from shutil import rmtree
        if not ids:
            return False
        errors = []
        if type(ids) is str:
            ids = (ids,)
        for i in ids:
            try:
                path = Query.job_path_for_id(i)
                if os.path.exists( path ):
                    rmtree( path )
                else:
                    Config.logger.info("expire_now: no {} to expire".format(i))
            except OSError as e:
                errors.append(i)
                Config.logger.error("Query: Unable to delete {}: {}".format(i, str(e)))
            except:
                errors.append(i)
                Config.logger.error("Query: Unable to delete {}".format(i))
        return errors

def parse_json():
    """ reads form or argument key=value pairs from the thread local request object
        transforms it into q_fields for _build_query
    """
    # TODO - posted json content REQUIRES a JSON content-type header.  I'd like to auto detect
    # NOTE: The whole request parser part of Flask-RESTful is slated for removal ... use marshmallow.
    # JK 2017-11: RequestParser uses the 'context local' request object.  Here's a totally insufficient explanation:
    # https://stackoverflow.com/questions/4022537/context-locals-how-do-they-make-local-context-variables-global#4022729

    # we explain a bunch of arguments to reqparse, and parse_args() gives us a dictionary to return or spits an exception
    rp = reqparse.RequestParser(trim=True, bundle_errors=True)

    rp.add_argument('sensor', action='append', default=[], type=lambda x: str(x),
                    help='Name of sensors to query, matches sensor names in docket config (accepts multiple values)')
    rp.add_argument('host', action='append', default=[], type=lambda x: str(x),
                    help='IP address (accepts multiples)')
    rp.add_argument('net', action='append', default=[],  type=lambda x: str(x),
                    help='IP network with CIDR mask (accepts multiple values)')
    rp.add_argument('port', action='append', default=[],  type=lambda x: str(x),
                    help='IP port number (TCP or UDP) (accepts multiple values)')
    rp.add_argument('proto', help='IP protocol number',  type=lambda x: str(x))
    rp.add_argument('proto-name', help='One of: TCP, UDP, or ICMP', type=lambda x: str(x))
    rp.add_argument('before', type=lambda x: str(x),
                    help='Datetime expressed as UTC RFC3339 string')
    rp.add_argument('after', type=lambda x: str(x),
                    help='Datetime expressed as UTC RFC3339 string')
    rp.add_argument('before-ago', type=lambda x: str(x),
                    help='Time duration expressed in hours (h) or minutes (m)')
    rp.add_argument('after-ago', type=lambda x: str(x),
                    help='Time duration expressed in hours (h) or minutes (m)')

    rp.add_argument('Steno-Limit-Packets', location=['headers', 'values'],
                    type=lambda x: str(x),
                    help='Limits the number of packets that each stenographer instance will return')
    rp.add_argument('Steno-Limit-Bytes', location=['headers', 'values'],
                    type=lambda x: str(x),
                    help='Limits the number of bytes that each stenographer instance will return')

    rp.add_argument('ignore-weight',
                    help='Override the configured weight limit for this request')

    q_fields = { k:v for k,v in rp.parse_args(strict=True).items() if v or v is 0}
    Config.logger.info(str(type(q_fields))[6:] + ": " + str(q_fields))
    return q_fields

def parse_uri(path):
    _usage = """
    USAGE:

    Support arbitrary REST query using following translated
    query (using stenographer API). All terms are AND'd together
    to refine the query. The API does not currently support OR semantics
    Time intervals may be expressed with any combination of: h, m, s, ms, us

    /host/1.2.3.4/ -> 'host 1.2.3.4'
    /host/1.2.3.4/host/4.5.6.7/ -> 'host 1.2.3.4 and host 4.5.6.7'
    /net/1.2.3.0/24/ -> 'net 1.2.3.0/24'
    /port/80/ -> 'port 80'
    /proto/6/ -> 'ip proto 6'
    /tcp/ -> 'tcp'
    /tcp/port/80/ -> 'tcp and port 80'
    /before/2017-04-30/ -> 'before 2017-04-30T00:00:00Z'
    /before/2017-04-30T13:26:43Z/ -> 'before 2017-04-30T13:26:43Z'
    /before/45m/ -> 'before 45m ago'
    /after/3h/ -> 'after 180m ago'
    /after/3h30m/ -> 'after 210m ago'
    /after/3.5h/ -> 'after 210m ago'

    Example query using curl
    ```
    $ curl -s localhost:8080/pcap/host/192.168.254.201/port/53/udp/after/3m/ | tcpdump -nr -
    reading from file -, link-type EN10MB (Ethernet)
    15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
    15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
    ```
    """

    Config.logger.debug("arg: path => {}".format(path))

    q_fields = {
            'host': [],
            'net' : [],
            'port': [],
            'proto' : None,
            'proto-name' : None,
            'after-ago'  : None,
            'before-ago' : None,
            'after' : None,
            'before' : None,
            }

    state = None
    for arg in path.split('/'):
        if state is None:
            if arg.upper() in ("HOST", "NET", "PORT", "PROTO", "BEFORE", "AFTER"):
                state = arg.upper()
            elif arg.upper() in ("UDP", "TCP", "ICMP"):
                q_fields['proto-name']= arg.lower()
                continue
            elif arg.upper() in ("IGNORE-WEIGHT", ""):
                continue
            else:
                raise BadRequest("Unrecognized clause in URI: {}".format(arg))
        elif state == "HOST":
            q_fields[state.lower()].append(arg)
            state = None
        elif state == "PORT":
            q_fields[state.lower()].append(int(arg))
            state = None
        elif state == "PROTO":
            q_fields[state.lower()].append(arg)
            state = None
        elif state == "NET":
            # Read a network, then look for a mask
            q_fields['nettmp']=arg
            state = "NET1"
        elif state == "NET1":
            q_fields['net'].append("{}/{}".format(q_fields['nettmp'], arg))
            state = None
            del(q_fields['nettmp'])
        elif state in ["BEFORE", "AFTER"]:
            q_fields[state.lower()] = arg
            state = None

    if state != None:
        raise BadRequest("Incomplete {} clause".format(state))
    return q_fields

class QueryRequest(Resource):
    """ This class handles Stenographer Query requests ala Flask-Restful. """

    def post(self):
        """ post - build a query based on submitted form or json
                 - enqueue it for processing
                 - return the ID, URL needed for a future get ID/MERGED_NAME.pcap request
        """
        Config.logger.info("query request: {}".format(_get_request_nfo()))
        low = space_low()
        if low:
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force':True})
            Config.logger.error(low)
            return low, 413

        try:
            fields = parse_json()
            q = Query(fields=fields)
        except BadRequest as e:
            return str(e), 400
        except ValueError as e:
            return str(e), 400
        return q.enqueue()

    def get(self, path):
        """ get  - build a query based on uri and enqueue it for processing
                 - return the ID, URL needed for a future get ID/MERGED_NAME.pcap request
        """
        Config.logger.info("URI request: {}".format(_get_request_nfo()))
        low = space_low()
        if low:
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force': True})
            Config.logger.error(low)
            return low, 413

        try:
            fields = parse_uri(path)
            q = Query(fields=fields)
        except BadRequest as e:
            return str(e), 400
        except ValueError as e:
            return str(e), 400

        result = q.enqueue()

        r = Response(
            response=dumps(result, default=json_serial),
            status=302,
            mimetype='application/json'
        )
        statusUrl = '{}/#/status/{}'.format(Config.get('UI_WEB_ROOT',''), result['id'])
        r.headers['Location'] = '{}'.format(statusUrl)
        return r

class RawRequest(Resource):
    """ This class handles RAW Stenographer Query requests. """
    def get(self, query):
        Config.logger.info("RAW request: {}".format(_get_request_nfo()))

        low = space_low()
        if low:
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force':True})
            Config.logger.error(low)
            return low

        from urllib import unquote_plus
        q = Query(unquote_plus(query))
        Config.logger.info("Raw query: {}".format(q.query))
        return q.enqueue()

    def post(self):
        """ Handles raw query POST,
            such as stenoread's "curl -d 'QUERY_STRING'"
            or curl -d '{ "query" : "QUERY_STRING" }'
        """
        Config.logger.info("RAW request: {}".format(_get_request_nfo()))

        low = space_low()
        if low:
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force':True})
            Config.logger.error(low)
            return low

        q = Query()
        q.query = ''
        for k,v in request.form.lists():
            if k == 'query':
                q.query += v
                break
            elif not v or v == [u'']:
                q.query += k

        Config.logger.info("Raw query: {}".format(q.query))
        return q.enqueue()

class ApiRequest(Resource):
    delims = re.compile('[, \t;+]+')

    def get(self, api=None, selected=None):
        """ inspect parameters and call the right Query method """
        Config.logger.info("API request: {}".format(_get_request_nfo()))

        if type(selected) is str:
            selected = self.__class__.delims.split(selected)

        if api == "ids" or api == "urls":
            ids = Query.get_unexpired(selected)
            if api == "ids":
                return ids
            urls = {}
            for i in ids:
                if os.path.exists(Query.pcap_path_for_id(i)):
                    urls[i] = Query.pcap_url_for_id(i)
            return urls

        elif api == "stats":
            from tasks import get_stats
            stats = get_stats(selected_sensors=selected)
            freespace = spool_space()
            stats['docket'] = {'Free space': freespace}
            return stats

        elif api == "status":
            r = Response(
                response=dumps(
                    Query.status_for_ids(Query.get_unexpired(selected)),
                    default=json_serial),
                mimetype="application/json"
                )
            return r

        elif api == "clean" or api == 'cleanup':
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force':True})
            return "Cleanup queued"

        elif api == "jobs":
            return Query.find({})

        return "Unrecognized request: try /stats, /ids, /urls, /jobs or POST a json encoded stenographer query"

    def post(self, api=None, selected=None):
        if api == 'find':
            fields = parse_json()
            Config.logger.info("Fields: {}".format(fields))
            return Query.find(fields)
        return "Unrecognized request: try /stats, /ids, /urls or POST a json encoded stenographer query"
