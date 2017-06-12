from flask_restful import Resource
from flask import Response, request, send_file

from pprint import PrettyPrinter
pp = PrettyPrinter()

STENO_HEADERS = ['Steno-Limit-Packets', 'Steno-Limit-Bytes']

class Pcap(Resource):
    def get(self, path):
        from tasks import get_stats
        pass

    def post(self):
        pass

class RawQuery(Resource):
    def post(self):
        from tasks import raw_query
        import os.path

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


