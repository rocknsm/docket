import requests
import yaml
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from docket import celery, app
from common.utils import is_sequence

logger = get_task_logger(__name__)

instances = app.flask_app.config['stenographer_instances']
TASK_STORAGE = '/tmp/docket/pcap'

app.flask_app.config['TASK_STORAGE_PATH'] = TASK_STORAGE

@celery.task(bind=True)
def raw_query(self, query, selected_sensors=None):
    logger.debug("Begin raw_query")

    import subprocess, os, os.path
    datas = []
    error = None

    job_path = os.path.join(
            app.flask_app.config['TASK_STORAGE_PATH'],
            self.request.id
        )
    os.mkdir(job_path, 0700)

    outputs = []
    for instance in instances:
        if (selected_sensors is None or
            ( is_sequence(selected_sensors) and
              instance['sensor'] in selected_sensors )):
            url = "https://%s:%i/query" % (
                   instance['host'], instance['port'])

            logger.debug("Processing instance: {}".format(instance['sensor']))

            #rq = requests.Request('POST', url, data=query).prepare()
            s = requests.Session()
            r = requests.post(url, data=query, cert=(instance['cert'], instance['key']), verify=instance['ca'])

            #r = requests.post(url,
            #            data=query,
            #            cert=(instance['cert'], instance['key']),
            #            verify=instance['ca']
            #        )
            logger.debug("Error {}: {}".format(r.status_code, r.reason))

            # Some error happened
            if r.status_code == 400:
                error = r.reason

            # Read response and write to temporary file
            elif r.status_code == 200:
                out_file = os.path.join(
                        job_path, 
                        "{}.pcap".format(instance['sensor'])
                        )

                with open(out_file, 'wb') as f:
                    f.write(r.content)

                outputs.append(out_file)
            else: # This was unexpected
                error = "Unexpeded error: {}".format(instance['sensor']) 

    if len(outputs) > 0:
        logger.debug("Processing {} outputs", len(outputs))

        # We have several files, lets merge them
        job_file = os.path.join(job_path, "{}.pcap".format(self.request.id))
        cmd = ["mergecap", "-F", "pcap", "-w", job_file]
        cmd.extend(outputs)

        logger.debug("Calling mergecap as: {}".format(" ".join(cmd)))
        proc = subprocess.Popen(cmd)
        proc.wait()

        # Cleanup temporary files
        if proc.returncode == 0:
            logger.debug("Removing temp files: {}".format(outputs))
            for item in outputs:
                os.remove(item)

        return (proc.returncode, job_file)
    else:
        return (-1, error)

@celery.task(bind=True)
def get_stats(self, selected_sensors=None):
    fn_name = "get_stats"
    logger.debug("Begin {}".format(fn_name))

    logger.debug("celery id: {}".format(self.request.id))
    datas = []


    for instance in instances:
        if (selected_sensors is None or
            ( is_sequence(selected_sensors) and
              instance['sensor'] in selected_sensors )):
            logger.debug("{}: query instance: {}".format(fn_name, instance['sensor']))

            url = "https://{}:{}/debug/stats".format(
                   instance['host'], instance['port'])

            r = requests.get(url, 
                    cert=(instance['cert'], instance['key']),
                    verify=instance['ca'])

            logger.debug("{}: response code: {}".format(fn_name, r.status_code))
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
            data['oldest_timestamp'] = dt.isoformat() + 'Z'
            #data['oldest_timestamp'] = dt
            data['sensor'] = instance['sensor']

            datas.append(data)

    logger.debug("End {}".format(fn_name))
    return datas
