import requests
import yaml, simplejson as json
import pprint
from datetime import datetime, timedelta
from rfc3339 import rfc3339

pp = pprint.PrettyPrinter()

selected_sensors = ["sensor-001"]

_conf_path = "./devel.yaml"
_config = {}
with open(_conf_path) as f:
    _config = yaml.load(f.read())

instances = _config['stenographer_instances']

for instance in instances:
    if instance['sensor'] in selected_sensors:
        url = "https://%s:%i/debug/stats" % (instance['host'], instance['port'])

        r = requests.get(url, cert=(instance['cert'], instance['key']), verify=instance['ca'])

        if r.status_code != 200:
            print "Shit guys! Someone is shooting at us!"

        lines = r.text.split('\n')
        data = {}
        for line in lines:
            if len(line.strip()) > 0:
                k, v = line.split()
                data[k] = int(v)

        ot = data['oldest_timestamp']

        dt = datetime.utcfromtimestamp(0) + timedelta(microseconds=ot/1000 )
        data['oldest_timestamp'] = dt.isoformat() + 'Z'
        data['sensor'] = instance['sensor']

        print(json.dumps(data))

