from flask_restful import Resource
from flask import Response, request, send_file
from datetime import datetime
import os.path
import re

from common.exceptions import HTTPException

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

def ceildiv(a, b):
    return int(-(-a // b))

def _parseDuration(s):
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


class PcapApi(Resource):
    def post(self):
        """
        Support form submission of PCAP query. Supports the following
        query terms translated to stenographer API.
        All terms are AND'd together to refine the query. The API does 
        not currently support OR semantics
        Time intervals may be expressed with any combination of: h or m

        # Query for a single host, net, or port
        host=1.2.3.4   -> 'host 1.2.3.4'
	net=1.2.3.0/24 -> 'net 1.2.3.0/24'       
        port=80        -> 'port 80'

        # Supports duplicate field names for host, net, port
        host=1.2.3.4   -> 'host 1.2.3.4 and host 4.5.6.7'
        host=4.5.6.7         

        # Query by protocol number
        proto=6        -> 'ip proto 6'
        
        # Query by common protocol name for tcp, udp, icmp
        proto-name=tcp -> 'tcp'

        # Combine protocol and port
        proto-name=tcp -> 'tcp and port 80'
        port=80

        # Query by time, requires RFC3339 datetime string specified in UTC
        before=2017-04-30T13:26:43Z -> 'before 2017-04-30T13:26:43Z'
        before=2017-04-30T00:00:00Z -> 'before 2017-04-30T00:00:00Z'

	# Query by relative time expressed in combination of hours and minutes
        before-ago=45m  -> 'before 45m ago'
        after-ago=3h    -> 'after 180m ago'
        after-ago=3h30m -> 'after 210m ago'
        after-ago=3.5h  -> 'after 210m ago'

	Example query using curl (form-encoded):
	```
        $ curl -s -XPOST localhost:8080/api/ -d 'host=192.168.254.201' -d 'proto-name=udp' -d 'port=53' -d 'after-ago=3m' | tcpdump -nr -
        reading from file -, link-type EN10MB (Ethernet)
        15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
        15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
        ```

        This interface also supports JSON-encoded queries (requires content-type):
        ```
        curl -s -XPOST localhost:8080/api/ -H 'Content-Type: application/json' -d '
        { "host": "192.168.254.201", "proto-name": "udp", "port": 53, "after-ago": "3m" }' | tcpdump -nr -
        reading from file -, link-type EN10MB (Ethernet)
        16:16:32.700658 IP 192.168.254.201.50169 > 205.251.195.137.domain: 27094% [1au] A? ping.example.net. (47)
        16:16:32.759907 IP 205.251.195.137.domain > 192.168.254.201.50169: 27094*- 8/4/1 A 198.18.209.234, A 198.18.232.30, ... 
        ```
        """
        from flask import current_app
        logger = current_app.logger
        from tasks import raw_query
 
        from flask_restful import reqparse
        parser = reqparse.RequestParser()

        parser.add_argument('sensor', action='append', default=[], store_missing=True,
                help='Name of sensors to query, matches sensor names in docket config (accepts multiple values)')
        parser.add_argument('host', action='append', default=[], store_missing=True,
                help='Single IP address (accepts multiple values)')
        parser.add_argument('net', action='append', default=[], store_missing=True,
                help='IP network with CIDR mask (accepts multiple values)')
        parser.add_argument('port', action='append', default=[], store_missing=True, 
                help='IP port number (TCP or UDP) (accepts multiple values)')
        parser.add_argument('proto', type=int, help='IP protocol number')
        parser.add_argument('proto-name', help='One of: TCP, UDP, or ICMP')
        parser.add_argument('before', 
                type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ'),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('after', 
                type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ'),
                help='Datetime expressed as UTC RFC3339 string')
        parser.add_argument('before-ago', 
                help='Time duration expressed in hours (h) or minutes (m)')
        parser.add_argument('after-ago', 
                help='Time duration expressed in hours (h) or minutes (m)')

        parser.add_argument('Steno-Limit-Packets', location=['headers', 'values'],
                help='Limits the number of packets that each stenographer instance will return')
        parser.add_argument('Steno-Limit-Bytes', location=['headers', 'values'],
                help='Limits the number of bytes that each stenographer instance will return')

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
                raise HTTPException(message="I'm a teapot.",
                        payload="USAGE: {}".format(_usage),
                        status_code=418 )
        if query['before']:
            qry_str.append('before {}'.format(query['before']))
        if query['after']:
            qry_str.append('after {}'.format(query['after']))
        if query['before-ago']:
            dur = _parseDuration(query['before-ago'])
            if dur is not None:
                qry_str.append('before {:d}m ago'.format(ceildiv(dur.total_seconds(),60)))
        if query['after-ago']:
            dur = _parseDuration(query['after-ago'])
            if dur is not None:
                qry_str.append('after {:d}m ago'.format(ceildiv(dur.total_seconds(),60)))
 

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
                    HTTPException(message="Response file not found", status_code=404)
            else:
                # Something failed
                HTTPException(message="RC: {}  Message: {}".format(rc, message), status_code=500)



class PcapUri(Resource):
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
                    raise HTTPException("I'm a teapot.",
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
                dur = _parseDuration(arg)
                if dur is not None:
                    logger.debug("Duration is: {}".format(dur.total_seconds()))
                    query[state.lower()] = "{:d}m ago".format(ceildiv(dur.total_seconds(),60))
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
                    HTTPException(message="Response file not found", status_code=404)
            else:
                # Something failed
                HTTPException(message="RC: {}  Message: {}".format(rc, message), status_code=500)

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
            else:
                HTTPException(message="Response file not found", status_code=404)
        else:
            # Something failed
            HTTPException(message="RC: {}  Message: {}".format(rc, message), status_code=500)
