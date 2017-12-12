# Query - A Class for tracking queries through the process and interfacing with them
# QueryRequest - implements Flask Restful to fill requests with formatted data
from collections import namedtuple
from datetime import datetime, timedelta
import re
import os

from werkzeug.exceptions import BadRequest
from flask import jsonify, request
from flask_restful import Resource, inputs, reqparse
import yaml

from common.utils import parse_duration, parse_capacity, file_modified, ISOFORMAT \
        , recurse_update, md5, validate_ip, validate_net, readdir, spool_space \
        , epoch, from_epoch, update_yaml, space_low 
from config import Config

RequestInfo = namedtuple('RequestInfo', 'ip port agent')
Event       = namedtuple('Event', 'datetime name msg state')

_DATE_FORMAT = Config.get('DATE_FORMAT', "%Y%jT%H:%M:%S")
_INSTANCES = Config.get('STENOGRAPHER_INSTANCES')
_SENSORS = []

for steno in _INSTANCES:
    steno['stats'] = {}
    _SENSORS.append(steno['sensor'])

Config.setdefault('TIME_WINDOW', 60)

def enforce_time_window(time):
    """ given a datetime, return the start time of it's TIME_WINDOW 
        aka - 'round down' a time into our TIME_WINDOW
    """
    if not Config.get('TIME_WINDOW'):
        return time
    return from_epoch(   epoch(time)
                      // Config.get('TIME_WINDOW')
                      *  Config.get('TIME_WINDOW'))

def _get_request_nfo():
    """ grab client info for logging, etc.. 
    request information might depend on our technology stack and this code was designed for nginx -> uwsgi
    """
    return RequestInfo(ip   = request.environ.get('REMOTE_ADDR', request.remote_addr), 
                       port = request.environ.get('REMOTE_PORT', '_UNKNOWN_'),
                       agent= request.environ.get('HTTP_USER_AGENT', '_UNKNOWN_')
                      )

class Query:
    """ Query               handles metadata and actions to process docket queries:
        q = Query()         creates an empty query
        q.build_query(f)   initialize the query
        q.enqueue()         send the query to celery to start processing.

        Query(f).enqueue()  shorthand
    """
    LONG_AGO = parse_duration(Config.get('LONG_AGO', '24h'))
    WEIGHTS = {
        'total' : parse_capacity(Config.get('WEIGHT_TOTAL',     '5TB')),
        'limit' : parse_capacity(Config.get('WEIGHT_THRESHOLD', '20MB')),
        'ip'    : Config.get('WEIGHT_IPS', 50.0),
        'net'   : Config.get('WEIGHT_NETS', 2.0),
        'port'  : Config.get('WEIGHT_PORTS', 100.0),
        'hour'  : Config.get('WEIGHT_HOURS', 8.0)
        }

    # Query.events can have a 'state': states are used to filter events for display
    RECEIVING = 'Requesting'
    RECEIVED= 'Request Complete'
    MERGE     = 'Merging'
    SUCCESS = 'Completed'
    ERROR = 'Error'
    FAIL = 'Failed'

    def __init__(self, fields=None, q_id=None):
        self.query     = None           # string: query formatted for stenoapi
        self.state     = None           # string: one of (RECEIVING, SUCCESS, ERROR, FAIL)
        self._id       = None           # a hash of the normalized query string, uniquely identifies this query to prevent duplicates
        self.events    = []             # a sorted list of events including errors

        if isinstance(q_id, str) and len(q_id) >= 32:
            self.load(q_id=q_id)

        elif isinstance(fields, dict):
            self.build_query(fields)

        elif fields:
            try:
                Config.logger.debug("updating: {} with {}".format(self, fields))
                self.detupify(fields)
            except TypeError as e:
                self.error('init', 'Unexpected values:{}'.format(fields))
                raise e

    def load(self, path=None, q_id=None):
        """ query data from disk, if no path is provided use the default (requires id) """
        if path is None:
            q_id = q_id or self._id
            if q_id:
                return update_yaml(Query.yaml_path_for_id(q_id), self) != False
        if path:
            if os.path.exists(path):
                return update_yaml(path, self) != False
            self.error('load', "No Such path {}".format(path))
        return False

    def save(self):
        """ save this query to the default location """
        self.load()
        
    def update(self, other):
        """ update self from other's data, 
            other can be a Query, dict, or yaml string.
        """
        Config.logger.debug("updating: {} with {}".format(self, other))
        if type(other) is dict and other:
            Config.logger.debug("Dict update: {} with {}".format(self, other))
            recurse_update(self.__dict__, { k:v for k,v in other.items() if v})
            self._fix_events()
            return True
        elif isinstance(other, Query):
            Config.logger.debug("instance update: {} with {}".format(self, other))
            recurse_update(self.__dict__, { k:v for k,v in other.__dict__.items() if v})
            self._fix_events()
            return True
        elif type(other) is str:
            return self.update(yaml.load(other))
        return False

    def tupify(self):       # We can't queue an object. This is all the data we need to use queue in the celery worker
        """ Serializes the basic values used to define a query into a tuple """
        return (self.query, self.requested.strftime(ISOFORMAT))

    def detupify(self, fields):
        self.query = fields[0]
        self.events = [Event(datetime=datetime.strptime(fields[1], ISOFORMAT), name='Requested', msg=None, state=None)]

    def _fix_events(self):
        """ resort events, the list order can be wrong when loaded from a file """
        self.events = sorted( self.events )

    @property
    def id(self):
        """ hexdigest of the query - uniquely identifies the request based on the query string (assumes query times are absolute) """
        if self._id is not None:
            return self._id
        elif self.query:
            # calculate a 'query' hash to be our id
            self._id = md5(self.query)
            if Config.get('ID_FORMAT', False) == '-':  # GUID style with dashes, easier to read but harder to copy paste
                self._id = '-'.join((self._id[:8], self._id[8:16], self._id[16:24], self._id[24:]))
            return self._id
        else:
            Exception("Can't create query.id")

    @property
    def requested(self):
        """ shortcut for the 'Requested' status time """
        return self.events[0].datetime

    @property
    def query_time(self):
        """ 'Requested' as used in the query string (adjusted for TIME_WINDOW) """
        return enforce_time_window(self.requested)

    def __str__(self):
        return "[{}]".format( self.id if self.query else "partial QUERY" )

    def is_requested(self):
        return len(self.events) > 0

    def time_requested(self):
        """ returns an ISO date (ordinal) - when the query was requested """
        return self.requested.strftime(_DATE_FORMAT)

    def time_expire(self):
        """ returns an ISO date (ordinal) - a guess when the query data will expire and become unavailable """
        return (self.requested + parse_duration(Config.get('EXPIRE_TIME', 3600))).strftime(_DATE_FORMAT)

    @property
    def yaml_path(self):
        return Query.yaml_path_for_id(self.id)

    @classmethod
    def yaml_path_for_id(cls, q_id):
        """  path used to record this query as yaml (if QUERY_NAME is set) """
        filename = Config.get('QUERY_NAME')
        if filename:
            return cls.job_path_for_id(q_id, filename+".yaml")

    @property
    def job_path(self):
        """ path for this query's artifacts """
        return self.job_path_for_id(self.id)

    @staticmethod
    def job_path_for_id(q_id, filename=None):  # ensure canonical naming - everything uses this function
        parts = (Config.get('SPOOL_DIR'), q_id)
        if filename:
            parts += (filename,)
        return os.path.join(*parts)

    def validate(self):
        """ performs any request time initialization and checks for validity """
        if not self.events:
            self.progress('Requested')
        return self.invalid

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

    def build_query(self, fields):
        Config.logger.debug("build_query {}".format(str(fields)))

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
        self.progress('Requested')

        start = self.query_time + self.LONG_AGO
        end   = self.query_time + timedelta(minutes=1)

        qry_str = []
        weights = {'ip': 0,
                   'net': 0,
                   'port': 0,
                   'hour': 0}
        for host in sorted(q_fields['host']):
            validate_ip(host)
            qry_str.append('host {}'.format(host))
            weights['host'] += 1
        for net in sorted(q_fields['net']):
            validate_net(net)
            qry_str.append('net {}'.format(net))
            weights['net'] += 1
        for port in sorted(q_fields['port']):
            if not 0 < int(port) < 65536:
                raise BadRequest("Port {} out of range".format(port))
            qry_str.append('port {}'.format(int(port)))
            weights['port'] += 1
        if q_fields['proto']:
            qry_str.append('ip proto {}'.format(q_fields['proto']))
        if q_fields['proto-name']:
            if q_fields['proto-name'].upper() not in ['TCP', 'UDP', 'ICMP']:
                raise BadRequest(description="Bad proto-name: {}".format(q_fields['proto-name']))
            qry_str.append(q_fields['proto-name'].lower())
        if q_fields['after-ago']:
            dur = parse_duration(q_fields['after-ago'])
            if dur is not None:
                q_fields['after'] = self.query_time - dur
        if q_fields['before-ago']:
            dur = parse_duration(q_fields['before-ago'])
            if dur is not None:
                q_fields['before'] = self.query_time - dur
        if q_fields['after']:
            start = enforce_time_window(q_fields['after'])
        if q_fields['before']:
            end = enforce_time_window(q_fields['before']) + timedelta(seconds=Config.get('TIME_WINDOW'))

        # Check the request's 'weight'
        req_weight = ( Query.WEIGHTS['total'] 
                      * (end-start).total_seconds() * Query.WEIGHTS['hour'] // 3600 
                      / (sum((val * Query.WEIGHTS[k] for k, val in weights.items())) or 1)
                     )

        if req_weight > Config.get('WEIGHT_THRESHOLD') and not q_fields.get('ignore-weight'):
            self.error('build_query', 
                       "Request is too heavy: {}/{}:\t{}".format(req_weight, 
                                                                 Config.get('WEIGHT_THRESHOLD'), 
                                                                 jsonify(q_fields)))
            raise BadRequest("Request parameters exceed maximum: {}/{}".format(req_weight, Config.get('WEIGHT_THRESHOLD')))

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

    def enqueue(self):
        """ queue this query in celery for fulfillment """
        error = self.validate()
        if error:
            raise Exception("Invalid Query " + str(error))
        from tasks import query_stenographer
        query_stenographer.apply_async(queue='query', kwargs={'query_tuple' :self.tupify()})
        return { 'id': self.id, 'Requested' : self.time_requested(), 'query': self.query, 'url' : self.pcap_url }

    @property
    def pcap_url(self):
        return self.pcap_url_for_id(self.id)

    @staticmethod
    def pcap_url_for_id(id=None):
        if id:
            return "{}{}/{}.pcap".format(Config.get('WEB_ROOT', '/'), id, Config.get('MERGED_NAME'))

    @property
    def pcap_path(self):
        return Query.pcap_path_for_id(self.id)

    @staticmethod
    def pcap_path_for_id(id):
        if id:
            return os.path.join(Config.get('SPOOL_DIR'), id, '%s.pcap' % Config.get('MERGED_NAME'))

    def complete(self):     
        """ why a separate method: because someone will definitely want to check for the 'completed' status so it better be reliably named """
        self.progress("Completed")

    def progress(self, name, msg=None, state=None):
        """ Record the time 'action' occurred """
        e = Event(datetime.utcnow(), name, msg, state)
        self.events.append(e)
        if state in (Query.ERROR, Query.FAIL):
            if (state == Query.FAIL) or (self.state != Query.FAIL):
                self.state = state 
            Config.logger.error("Query[{}] Error: {}:{}".format(self.id, name, msg or ''))
        else:
            if state and (self.state not in (Query.ERROR, Query.FAIL)):
                self.state = state
            Config.logger.info("Query[{}] {}:{}".format(self.id, name, msg or ''))

    @staticmethod
    def get_unexpired(ids=None):
        """ return a list of query IDs that are still available on the drive
            the queries can be in various states of processing
        """
        return [ f for f in readdir(Config.get('SPOOL_DIR'))
                if (f not in ['.', '..']) and
                    (not ids or f in ids) and
                    (len(f) >= 32) ]

    def status(self, full=False):
        """ describe the state of processing this query is in """
        if self.events:
            status = {
                'state': self.state,
                'requests': { act: (dt.strftime(_DATE_FORMAT), m, s)
                             for dt,act,m,s in self.events 
                             if act in _SENSORS
                            },
            }
            status['events']= [ (dt.strftime(_DATE_FORMAT),a,m,s) 
                               for dt,a,m,s in self.events
                               if full or s
                              ]
            return status
        else:
            merged_tmp = os.path.join(self.job_path, "merged.tmp")
            if self.invalid:
                result = self.errors.items()[-1][0]
                time   = "Unknown"
            elif os.path.exists( self.pcap_path ):
                result = "Complete"
                time   = file_modified( self.pcap_path, _DATE_FORMAT )
            elif os.path.exists( merged_tmp ):
                result = "Merging"
                time   = file_modified( merged_tmp, _DATE_FORMAT )
            elif os.path.exists( self.job_path ):
                result = "Requested"
                time   = file_modified( self.job_path, _DATE_FORMAT )
            else:
                result = "Unknown"
                time   = "Unknown"

        return { 'state': result }

    @staticmethod
    def status_for_ids(ids):
        """ return a dictionary of id : {status} """
        if type(ids) is str:
            ids = list(ids)

        results = {}
        for i in ids:
            q = Query(q_id=i)
            results.update( {i : q.status(full=True)} )
        return results

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

class QueryRequest(Resource):
    """ This class handles Stenographer Query requests ala Flask-Restful. """
    @staticmethod
    def parse_json():
        """ reads form or argument key=value pairs from the thread local request object and transforms it into a native query string """
        # TODO - posted json content REQUIRES a JSON content-type header.  I'd like to auto detect
        # NOTE: The whole request parser part of Flask-RESTful is slated for removal ... use marshmallow.
        # JK 2017-11: RequestParser uses the 'context local' request object.  Here's a totally insufficient explanation:
        # https://stackoverflow.com/questions/4022537/context-locals-how-do-they-make-local-context-variables-global#4022729

        # we explain a bunch of arguments to reqparse, and parse_args() gives us a dictionary to return or spits an exception
        parser = reqparse.RequestParser(trim=True, bundle_errors=True)

        parser.add_argument('sensor', action='append', default=[], store_missing=True,
                type=lambda x: x if x in _INSTANCES else ValueError("{} is not a valid sensor".format(x)),
                help='Name of sensors to query, matches sensor names in docket config (accepts multiple values)')
        parser.add_argument('host', action='append', default=[], store_missing=True,
                type=lambda x: validate_ip(x)[0],
                help='IP address (accepts multiples)')
        parser.add_argument('net', action='append', default=[], store_missing=True,
                type=lambda x: validate_net(x)[0],
                help='IP network with CIDR mask (accepts multiple values)')
        parser.add_argument('port', action='append', default=[], store_missing=True, type=int,
                help='IP port number (TCP or UDP) (accepts multiple values)')
        parser.add_argument('proto', type=int, help='IP protocol number')
        parser.add_argument('proto-name', type=inputs.regex(r'^(?i)(TCP|UDP|ICMP)$'), help='One of: TCP, UDP, or ICMP')
        parser.add_argument('before',
                type=lambda x: inputs.datetime_from_iso8601(x).replace(tzinfo=None),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('after',
                type=lambda x: inputs.datetime_from_iso8601(x).replace(tzinfo=None),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('before-ago',
                help='Time duration expressed in hours (h) or minutes (m)')
        parser.add_argument('after-ago',
                help='Time duration expressed in hours (h) or minutes (m)')

        parser.add_argument('Steno-Limit-Packets', type=int, location=['headers', 'values'],
                help='Limits the number of packets that each stenographer instance will return')
        parser.add_argument('Steno-Limit-Bytes', type=int, location=['headers', 'values'],
                help='Limits the number of bytes that each stenographer instance will return')

        parser.add_argument('ignore-weight', type=inputs.boolean,
                help='Override the configured weight limit for this request')

        q_fields = parser.parse_args(strict=True)
        Config.logger.info(str(type(q_fields))[6:] + ": " + str(q_fields))
        return q_fields

    @staticmethod
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
                if parse_duration(arg):
                    q_fields[state.lower()+'-ago'] = arg
                else:
                    try:
                        q_fields[state.lower()] = inputs.datetime_from_iso8601(arg)
                    except Exception as e:
                        raise ValueError("Unrecognized time in URI: {}".format(arg))
                state = None

        if state != None:
            raise BadRequest("Incomplete {} clause".format(state))
        return q_fields

    def post(self):
        """ post - build a query based on submitted form or json
                 - enqueue it for processing
                 - return the ID, URL needed for a future get ID/MERGE_NAME.pcap request
        """
        Config.logger.info("query request: {}".format(_get_request_nfo()))
        low = space_low()
        if low:
            Config.logger.error(low)
            return low

        try:
            fields = self.parse_json()
            q = Query(fields=fields)
        except BadRequest as e:
            return str(e)
        except ValueError as e:
            return "400 Bad Request:" + str(e)
        return q.enqueue()

    def get(self, path):
        """ get  - build a query based on uri and enqueue it for processing
                 - return the ID, URL needed for a future get ID/MERGE_NAME.pcap request
        """
        Config.logger.info("URI request: {}".format(_get_request_nfo()))
        low = space_low()
        if low:
            Config.logger.error(low)
            return low

        try:
            fields = self.parse_uri(path)
            q = Query(fields=fields)
        except BadRequest as e:
            return str(e)
        except ValueError as e:
            return "400 Bad Request:" + str(e)
        return q.enqueue()

class RawRequest(Resource):
    """ This class handles RAW Stenographer Query requests. """
    def get(self, query):
        Config.logger.info("RAW request: {}".format(_get_request_nfo()))

        low = space_low()
        if low:
            Config.logger.error(low)
            return low

        q = Query()
        # TODO - use a proper uri decoder
        q.query = query.replace("+", " ")
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
            for id in ids:
                if os.path.exists(Query.pcap_path_for_id(id)):
                    urls[id] = Query.pcap_url_for_id(id)
            return urls

        elif api == "stats":
            from tasks import get_stats
            stats = get_stats(selected_sensors=selected)
            freespace = spool_space()
            stats['docket'] = {'Free space': freespace}
            return stats 

        elif api == "status":
            return Query.status_for_ids(Query.get_unexpired(selected))

        elif api == "clean" or api == 'cleanup':
            from tasks import cleanup
            cleanup.apply_async(queue='io', kwargs={'force':True})
            return "Cleanup queued"

        return "Unrecognized request: try /stats, /ids, /urls or POST a json encoded stenographer query"
