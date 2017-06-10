import requests
import yaml
from flask import jsonify
from datetime import datetime, timedelta
import pprint
pp = pprint.PrettyPrinter()
from docket import celery, app

def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

instances = app.flask_app.config['stenographer_instances']

@celery.task()
def get_pcap(selected_sensors=None):
    pass

@celery.task()
def get_stats(selected_sensors=None):
    datas = []
    for instance in instances:
        if (selected_sensors is None or
            ( is_sequence(selected_sensors) and
              instance['sensor'] in selected_sensors )):
            url = "https://%s:%i/debug/stats" % (
                   instance['host'], instance['port'])

            r = requests.get(url, 
                    cert=(instance['cert'], instance['key']),
                    verify=instance['ca'])

            if r.status_code != 200:
                return json.dumps({})

            lines = r.text.split('\n')
            data = {}
            for line in lines:
                if len(line.strip()) > 0:
                    k, v = line.split()
                    data[k] = int(v)

            ot = data['oldest_timestamp']
            dt = datetime.utcfromtimestamp(0) + timedelta(microseconds=ot/1000 )
            #data['oldest_timestamp'] = dt.isoformat() + 'Z'
            data['oldest_timestamp'] = dt
            data['sensor'] = instance['sensor']

            datas.append(data)

    return datas
