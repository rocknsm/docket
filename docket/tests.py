from __future__ import print_function
from werkzeug.exceptions import BadRequest
from flask import Flask
from config import Config
from common.utils import *
import unittest
import os
from stat import S_ISDIR, ST_MODE

class testConfig(unittest.TestCase):
    def test_load(self):
        # TODO - Absolute path          "./test/test.yaml"
        filename = os.path.join(os.curdir, 'test', 'test.yaml')
        Config.load(filename, env={'MERGED_NAME': 'envOverride', 'new_val': 'value'})
        self.assertIsNone(Config.get("NOT_CONFIGURED"))
        self.assertEqual(Config.get('SECRET_KEY'), 'ITS_A_SECRET_TO_EVERBODY')
        self.assertEqual(Config.get('MERGED_NAME'), 'envOverride')
        self.assertEqual(Config.get('new_val'), 'value')
        if not os.path.exists(Config.get('SPOOL_DIR')):
            os.mkdir(Config.get('SPOOL_DIR'), 700)

    def test_defaults(self):
        self.assertEqual(Config.get('WEB_ROOT'), None)
        self.assertEqual(Config.get('TEST_DEFAULT_1'), None)
        self.assertEqual(Config.setdefault('TEST_DEFAULT_1', 1), 1)
        self.assertEqual(Config.get('TEST_DEFAULT_1'), 1)
        self.assertEqual(Config.get('TEST_DEFAULT_1', minval=2), 2)
        self.assertEqual(Config.get('TEST_DEFAULT_1'), 2) 
        with self.assertRaises(ValueError, msg="conflicting defaults"):
            Config.get('TEST_DEFAULT_1', default=2)
        with self.assertRaises(ValueError, msg="default < minval"):
            Config.get('TEST_DEFAULT_1', default=1, minval=2)

class testUtils(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(parse_duration("20.5h 25m 300s").total_seconds(), 3600 * 21)
        self.assertEqual(parse_duration("1d ago").total_seconds(), 3600 * 24)
        self.assertEqual(parse_duration("1w 1d").total_seconds(), 3600 * 24 * 8)
        self.assertEqual(parse_duration("5").total_seconds(), 5)
        self.assertEqual(parse_duration("3.15").total_seconds(), 3.15)

    def test_parse_capacity(self):
        self.assertEqual(parse_capacity(100), 100)
        self.assertEqual(parse_capacity("25"), 25)
        self.assertEqual(parse_capacity("0.5 TB 1GB 1mb 50b"), 
                (1024**4)/2.0 + 1024**3 + 1024**2 + 50)
        return

    def test_time(self):
        from datetime import datetime, timedelta
        self.assertEqual(datetime(1970, 1, 1) + timedelta(seconds=100), from_epoch(100) )
        self.assertEqual(epoch(datetime(1970, 1, 2)), timedelta(days=1).total_seconds())

    def test_recurse_update(self):
        a = { 
                '3': 1,
                '1': 1, 
                'map': {'set':'set', 'unset':None},
                'extend': [(1, 1), (3, 3)],
                'three': (1, 2, 5),}
        b = { 
                '3': 3,
                '1': None, 
                'map': {'set': None, 'unset': 'unset', 'new': 'new'},
                'extend': [(2, 2), (1, 1)],
                'three': 'three'}
        c = recurse_update(a,b, ignore_none=True)
        self.assertEqual(c, a)
        for k,v in c.items():
            if type(v) in (int, str):
                self.assertEqual(k, str(v))
            elif type(v) is dict:
                for i,j in v.items():
                    self.assertEqual(i, j, msg="{} {}:{}".format(k,i,j))
            elif type(v) is list:
                v.sort()
                self.assertEqual(v, [ (i, i) for i in range(1, len(v)+1)])
            elif type(v) is tuple:
                self.assertEqual(v, tuple(k.split()), msg="{}, {}".format(v,k))

class testIO(unittest.TestCase):
    def test_merge(self):
        # TODO - write a few caps, call merge, check merged.pcap
        #from resources.query import Query
        #q = Query()
        #from tasks import merge
        #merge()
        pass

    def test_cleanup(self):
        pass

class testQuery(unittest.TestCase):
    app = Flask('test')
    tests = [ 
        ( {'after': "1.2h3.4m5.6s"}, {'after': "1.2h3.4m5.6s"} ),
        ( {'after': "noon"},  401),
        ( {'after': "5"},  401),
        ( {'host': "1.2.3.4"}, {'host': ['1.2.3.4']}),
        ( {'host': "1.2.300.4"}, 400 ),
        ( {'net': "1.2.3.4/24"}, {'net':['1.2.3.4/24']}),
        ( {'net': "1.2.3.4/33"}, 400 ),
        ( {'net': "1.2.3.4/255.255.0.0"}, {'net':['1.2.3.4/255.255.0.0']}),
        ( {'net': "::1/33"}, {'net':['::1/33']}),
        ( {'net': "::1/129"}, 400 ),
        ( {'net': "::1/255.255.0.0"}, 400),
        ( {'port': "80"}, {'port':[80]}),
        ( {'port': "66000"}, 400), 
        ]
    def off_test_query_json_parser(self):
        import json
        self.assertTrue( S_ISDIR(os.stat(Config.get('SPOOL_DIR'))[ST_MODE] ))
        for r in testQuery.tests:
            from resources.query import parse_json
            query = json.dumps(r[0])
            correct = r[1]

            result = None
            # make sure we return or fail as described... NOTE: assertRaises only takes 'msg' in python3
            if type(correct) == type and issubclass(correct, Exception):
                with self.assertRaises(correct, msg="json: >{}<".format(query)):
                    with testQuery.app.test_request_context(
                        data=query
                    ):
                        result = parse_json()
            else:
                with testQuery.app.test_request_context(
                    data=query
                ):
                    result = parse_json()
                if result != correct:
                    if type(correct) == dict:
                        for k,v in [ (k, v) for k,v in correct.items() if v]:
                            self.assertEqual( v, result[k], msg="json: >{}< returned: {}".format(query, result) )
                    elif type(result) == str:
                        self.assertEqual( correct, 
                                int(result.split()[0]), msg="json: >{}< returned: {}".format(query, result) )

        # TODO - test stenographer instances:File "/opt/rocknsm/docket/docket/resources/query.py", line 13,

        # TODO - I need QueryRequest to take data from me instead of a 'real' webserver
        # TODO - test JSON -> q_fields
        # TODO - test q_fields -> query strings

    def test_query_uri_parser(self):
        from resources.query import parse_uri
        for query, correct in testQuery.tests:
            result = None
            query = '/' + "/".join(*query.items())
            # make sure we return or fail as described... NOTE: assertRaises only takes 'msg' in python3
            if type(correct) == type and issubclass(correct, Exception):
                with self.assertRaises(correct, msg="uri: {}".format(query)):
                    result = parse_uri(query)
            else:
                result = parse_uri(query)
                if result != correct:
                    if type(correct) == dict:
                        for k,v in [ (k, v) for k,v in correct.items() if v]:
                            self.assertEqual( v, result[k], msg="uri: {} returned: {}".format(query, result) )
                    elif type(result) == str:
                        self.assertEqual( correct, 
                                int(result.split()[0]), msg="uri: {} returned: {}".format(query, result) )

        # TODO - test stenographer instances:File "/opt/rocknsm/docket/docket/resources/query.py", line 13,
        # TODO - I need QueryRequest to take data from me instead of a 'real' webserver
        # TODO - test JSON -> q_fields
        # TODO - test q_fields -> query strings


unittest.main()
