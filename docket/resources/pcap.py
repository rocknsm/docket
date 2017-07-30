from flask_restful import Resource
from flask import Response, request, send_file, abort
from datetime import datetime
import re

from common.exceptions import InvalidUsage

STENO_HEADERS = ['Steno-Limit-Packets', 'Steno-Limit-Bytes']

HOURS   = r'(?P<hours>[\d.]+)\s*(?:h)'
MINUTES = r'(?P<minutes>[\d.]+)\s*(?:m)'
SECONDS = r'(?P<seconds>[\d.]+)\s*(:?s)'
MILLIS  = r'(?P<millis>[\d.]+)\s*(:?ms)'
MICROS  = r'(?P<micros>[\d.]+)\s*(:?us)'

OPT     = lambda x: r'(?:{x}\s*)?'.format(x=x)

TIMEFORMATS = [
        r'{HOURS}\s*{MINUTES}\s*{SECONDS}\s*{MILLIS}\s*{MICROS}\s*'.format(
            HOURS=OPT(HOURS),
            MINUTES=OPT(MINUTES),
            SECONDS=OPT(SECONDS),
            MILLIS=OPT(MILLIS),
            MICROS=OPT(MICROS)
            ),
        ]

MULTIPLIERS = dict([
    ('weeks',   60 * 60 * 24 * 7),
    ('days',    60 * 60 * 24),
    ('hours',   60 * 60),
    ('minutes', 60),
    ('seconds', 1),
    ('millis',  0.001),
    ('micros',  0.000001),
])

class Pcap(Resource):
    def _parseDuration(self, s):
        from flask import current_app
        logger = current_app.logger
        from datetime import timedelta

        for timefmt in TIMEFORMATS:
            logger.debug("timefmt is {}".format(timefmt))
            match = re.match(r'\s*' + timefmt + r'\s*$', s, re.I)
            logger.debug("Match is {}".format(match))
            if match and match.group(0).strip():
                mdict = match.groupdict()
                logger.debug("mdict is {}".format(mdict))
                return timedelta(seconds=sum(
                    [MULTIPLIERS[k] * float(v) for (k, v) in
                        list(mdict.items()) if v is not None]))

    def post(self, path=""):
        """
        Support form submission of PCAP query. Supports the following
        query terms.

        """
        from flask import current_app
        logger = current_app.logger
        from tasks import raw_query
 
        from flask_restful import reqparse
        parser = reqparse.RequestParser()

        parser.add_argument('sensor', action='append',
                help='Name of sensors to query, matches sensor names in docket config (accepts multiple values)')
        parser.add_argument('host', action='append',
                help='Single IP address (accepts multiple values)')
        parser.add_argument('net', action='append',
                help='IP network with CIDR mask (accepts multiple values)')
        parser.add_argument('port', action='append', 
                help='IP port number (TCP or UDP) (accepts multiple values)')
        parser.add_argument('proto', type=int, help='IP protocol number')
        parser.add_argument('proto-name', help='One of: TCP, UDP, or ICMP')
        parser.add_argument('before', 
                type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ'),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('after', 
                type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ'),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('before_ago', 
                help='Time duration expressed in hours (h), minutes (m), seconds (s), millis (ms), or micros (us)')
        parser.add_argument('after_ago', 
                help='Time duration expressed in hours (h), minutes (m), seconds (s), millis (ms), or micros (us)')

        parser.add_argument('Steno-Limit-Packets', location=['headers', 'values'],
                help='Limits the number of packets that each stenographer instance will return')
        parser.add_argument('Steno-Limit-Bytes', location=['headers', 'values'],
                help='Limits the number of bytes that each stenographer instance will return')

        query = parser.parse_args()

        # Build the query string
        qry_str = []
        for host in query['host']:
            qry_str.append('host {}'.format(host))
        for net in query['net']:
            qry_str.append('net {}'.format(net))
        for port in query['port']:
            qry_str.append('port {}'.format(port))
        if query['proto']:
            qry_str.append('ip proto {}'.format(query['proto']))
        if query['proto-name']:
            if query['proto-name'].upper() in ['TCP', 'UDP', 'ICMP']:
                qry_str.append(query['proto-name'].lower())
            else:
                _usage = "proto-name: {}".format(
                    [x for x in query.args if x.name == 'proto-name'][0].help
                    )
                raise InvalidUsage("I'm a teapot.",
                        payload="USAGE: {}".format(_usage),
                        status_code=418 )
        if query['before']:
            qry_str.append('before {}'.format(query['before']))
        if query['after']:
            qry_str.append('after {}'.format(query['after']))
        if query['before-ago']:
            dur = self._parseDuration(arg)
            if dur is not None:
                qry_str.append('before {}s ago'.format(dur.total_seconds()))
        if query['after-ago']:
            dur = self._parseDuration(arg)
            if dur is not None:
                qry_str.append('after {}s ago'.format(dur.total_seconds()))
 

        _query = " and ".join(qry_str)
        logger.debug("Query String: {}".format(_query))
        result = raw_query.apply_async(kwargs={'query': _query})

        while not result.ready():
            pass

        if result.successful():
            rc, message = result.result

            # Everything is normal
            if rc == 0:
                if os.path.isfile(message):
                    fname = os.path.basename(message)
                    rv = send_file(
                        message, 
                        mimetype='application/vnd.tcpdump.pcap',
                        as_attachment=True,
                        attachment_filename=fname
                        )
                    return rv
                else:
                    abort(404, message="Response file not found")
            else:
                # Something failed
                abort(500, message="RC: {}  Message: {}".format(rc, message))

    def get(self, path):
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
        /after/3h/ -> 'after 3h ago'
        /after/3h30m/ -> 'after 3h30m ago'
        /after/3.5h/ -> 'after 3h30m ago'

        """
        from flask import current_app
        logger = current_app.logger
        from tasks import raw_query
        import re, rfc3339, os.path
        from datetime import timedelta

        logger.debug("Entering Pcap::get")
        logger.debug("arg: path => {}".format(path))
        
        TIME_WINDOW = current_app.config["TIME_WINDOW"]

        _path = path.strip('/')

        logger.debug("Query: {}".format(_path))
        state = None
        argv = _path.split('/')

        query = {
                'host': [],
                'net' : [],
                'port': [],
                'proto': None,
                'udp': None,
                'tcp': None,
                'icmp': None,
                'before': None,
                'after': None,
                }
        for arg in argv:
            if state == None: 
                if arg.upper() in ["HOST", "NET", "PORT", "PROTO", "BEFORE", "AFTER"]:
                    state = arg.upper()
                elif arg.upper() in ["UDP", "TCP", "ICMP"]:
                    query[arg.lower()] = True
                    state = None
                else:
                    raise InvalidUsage("I'm a teapot.",
                            payload="{}".format(_usage),
                            status_code=418 )
            elif state in ["HOST", "PORT", "PROTO"]:
                # Read an IP
                query[state.lower()].append(arg)
                state = None
            elif state == "NET":
                # Read a network, leave mask blank
                query['net'].append((arg, None))
                state = "NET1"
            elif state == "NET1":
                query['net'][-1] = (query['net'][-1][0], arg)
                state = None
            elif state in ["BEFORE", "AFTER"]:
                # Test if this is indicating a relative time
                # Match on h, m, s, ms, us 
                dur = self._parseDuration(arg)
                if dur is not None:
                    logger.debug("Duration is: {}".format(dur.total_seconds()))
                    query[state.lower()] = "{}s ago".format(dur.total_seconds())
                else:
                    try:
                        dt = rfc3339.parse_datetime(arg).replace(tzinfo=None)
                        if state == "BEFORE":
                            dt = dt + timedelta(seconds=TIME_WINDOW)
                        else: # This is obviously AFTER
                            dt = dt - timedelta(seconds=TIME_WINDOW)
                        query[state.lower()] = "{}Z".format(dt.isoformat())
                    except ValueError:
                        logger.debug("Failed to parse datetime: {}".format(arg))
                state = None

        # Arg parsing complete
        logger.debug("Query: {}".format(query))

        # Build the query string
        qry_str = []
        for host in query['host']:
            qry_str.append('host {}'.format(host))
        for net in query['net']:
            qry_str.append('net {}/{}'.format(net[0], net[1]))
        for port in query['port']:
            qry_str.append('port {}'.format(port))
        if query['proto']:
            qry_str.append('ip proto {}'.format(query['proto']))
        if query['udp']:
            qry_str.append('udp')
        if query['tcp']:
            qry_str.append('tcp')
        if query['icmp']:
            qry_str.append('icmp')
        if query['before']:
            qry_str.append('before {}'.format(query['before']))
        if query['after']:
            qry_str.append('after {}'.format(query['after']))

        _query = " and ".join(qry_str)
        logger.debug("Query String: {}".format(_query))

        result = raw_query.apply_async(kwargs={'query': _query})

        while not result.ready():
            pass

        if result.successful():
            rc, message = result.result

            # Everything is normal
            if rc == 0:
                if os.path.isfile(message):
                    fname = os.path.basename(message)
                    rv = send_file(
                        message, 
                        mimetype='application/vnd.tcpdump.pcap',
                        as_attachment=True,
                        attachment_filename=fname
                        )
                    return rv
                else:
                    abort(404, message="Response file not found")
            else:
                # Something failed
                abort(500, message="RC: {}  Message: {}".format(rc, message))

class RawQuery(Resource):
    def post(self):
        from flask import current_app
        logger = current_app.logger
        from tasks import raw_query
        import os.path

        logger.debug("Entering RawQuery::post")

        query = request.form.lists()[0][0]
        headers = {
                key: value for (key, value) in request.headers.iteritems() if key in STENO_HEADERS }

        result = raw_query.apply_async(kwargs={'query': query, 'headers': headers})

        while not result.ready():
            pass

        if result.successful():
            rc, message = result.result

            # Everything is normal
            if rc == 0 and os.path.isfile(message):
                fname = os.path.basename(message)
                rv = send_file(
                        message, 
                        mimetype='application/vnd.tcpdump.pcap',
                        as_attachment=True,
                        attachment_filename=fname
                        )
                return rv


