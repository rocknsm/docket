from flask_restful import Resource
from flask import Response, request, send_file

from pprint import PrettyPrinter
pp = PrettyPrinter()

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
        pp.pprint("Query: {}".format(query))
        result = raw_query.apply_async(kwargs={'query': query})

        while not result.ready():
            pass

        pp.pprint(result.result)
        if result.successful():
            rc, message = result.result
            pp.pprint(result)

            # Everything is normal
            if rc == 0 and os.path.isfile(message):
                fname = os.path.basename(message)
                pp.pprint(fname)
                rv = send_file(
                        message, 
                        mimetype='application/vnd.tcpdump.pcap',
                        as_attachment=True,
                        attachment_filename=fname
                        )
                pp.pprint(rv)
                return rv


