from __future__ import print_function
from config import Config
import unittest
import os
from stat import S_ISDIR, ST_MODE

class testConfig(unittest.TestCase):
    def test_utils(self):
        pass

    def test_load(self):
        # TODO - Absolute path          "./test/test.yaml"
        filename = filename=os.path.join(os.curdir, 'test', 'test.yaml')
        Config.load(filename)
        self.assertIsNone(Config.get("NOT_CONFIGURED"))
        self.assertEqual(Config.get('SECRET_KEY'), 'ITS_A_SECRET_TO_EVERBODY')
        if not os.path.exists(Config.get('SPOOL_DIR')):
            os.mkdir(Config.get('SPOOL_DIR'), 700)
        # TODO - test stenographer instances:File "/opt/rocknsm/docket/docket/resources/query.py", line 13,

    def test_query_uri_parser(self):
        self.assertTrue( S_ISDIR(os.stat(Config.get('SPOOL_DIR'))[ST_MODE] ))
        # TODO - test uri -> q_fields
        uri = [ 
            ( "/after/1.2h3.4m5.6s", {'after-ago': "1.2h3.4m5.6s"} ),
            ( "/after/noon",  ValueError),
            ( "/after/5",  ValueError),
            ( "/host/1.2.3.4", {'host': ['1.2.3.4']}),
            ( "/host/1.2.300.4", 400 ),
            ( "/net/1.2.3.4/24", {'net':['1.2.3.4/24']}),
            ( "/net/1.2.3.4/33", 400 ),
            ( "/net/1.2.3.4/255.255.0.0", {'net':['1.2.3.4/255.255.0.0']}),
            ( "/net/::1/33", {'net':['::1/33']}),
            ( "/net/::1/129", 400 ),
            ( "/net/::1/255.255.0.0", 400),
            ( "/port/80", {'port':[80]}),
            ( "/port/66000", 400), 
        ]
        for u in uri:
            from resources.query import QueryRequest
            result = None
            # make sure we return or fail as described... NOTE: assertRaises only takes 'msg' in python3
            if type(u[1]) == type and issubclass(u[1], Exception):
                with self.assertRaises(u[1], msg="uri: {}".format(u[0])):
                    result = QueryRequest.parse_uri(u[0])
            else:
                result = QueryRequest.parse_uri(u[0])
                if result != u[1]:
                    if type(u[1]) == dict:
                        for k,v in [ (k, v) for k,v in u[1].items() if v]:
                            self.assertEqual( v, result[k], msg="uri: {} returned: {}".format(u[0], result) )
                    elif type(result) == str:
                        self.assertEqual( u[1], int(result.split()[0]), msg="uri: {} returned: {}".format(u[0], result) )


        # TODO - I need QueryRequest to take data from me instead of a 'real' webserver
        # TODO - test JSON -> q_fields
        # TODO - test q_fields -> query strings

    def test_merge(self):
        # TODO - write a few caps, call merge, check merged.pcap
        #from resources.query import Query
        #q = Query()
        #from tasks import merge
        #merge()
        pass

    def test_cleanup(self):
        pass
unittest.main()
