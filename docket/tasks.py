""" Celery Tasks (occasionally called from uwsgi: get_stats) """
import os
from os.path import join

from datetime import datetime, timedelta
from time import sleep
import requests

from docket import celery
from config import Config
from common.utils import parse_duration, parse_capacity, from_epoch, ISOFORMAT, file_modified, \
        spool_space, readdir, is_sequence
from resources.query import Query


#logger = Config.logger
_LAST_CLEANED = datetime.utcnow()

_INSTANCES = Config.get('STENOGRAPHER_INSTANCES')
for _ in _INSTANCES:
    _['idle'], _['stats']  = (from_epoch(0), {})

# IDLE_TIME     - 5, assume stenoboxes remain IDLE for 5 seconds and check again after that.
# IDLE_SLEEP    - 2.0, wait time between IDLE queries. will occur at least every IDLE_TIME.
# STAT_TIMEOUT  - 3.0, assume stenoboxes are broken if stats doesn't return in this many seconds
# QUERY_TIMEOUT - 720, assume stenoboxes are broken if a query doesn't return in this many seconds
IDLE_TIME       = Config.setdefault('IDLE_TIME', 5, min=1)
IDLE_SLEEP      = Config.setdefault('IDLE_SLEEP', 2.0, min=0)
STAT_TIMEOUT    = Config.setdefault('STAT_TIMEOUT', 3.0, min=0.1)
QUERY_TIMEOUT   = Config.setdefault('QUERY_TIMEOUT', 720.0, min=5)
MERGED_NAME     = Config.setdefault('MERGED_NAME', "merged")

EXPIRE_TIME     = parse_duration(Config.get('EXPIRE_TIME', 0))
EXPIRE_SPACE    = parse_capacity(Config.get('EXPIRE_SPACE', 0))

def get_stats(selected_sensors=None):
    """ return a dictionary of { sensorname: {stats} }
        NOTE: runs immediately not - used when we _need_ a result
    """
    Config.logger.debug("Get Stats:{}".format(selected_sensors))
    datas = {}

    global _INSTANCES
    for instance in _INSTANCES:
        if (    (selected_sensors is not None) and
                (selected_sensors != instance['sensor']) and
                (is_sequence(selected_sensors) and instance['sensor'] not in selected_sensors)):
            continue

        Config.logger.debug("query instance: {}".format(instance['sensor']))

        url = "https://{}:{}/debug/stats".format(
                instance['host'], instance['port'])

        rq = None
        try:
            rq = requests.get(
                url,
                cert=(instance['cert'], instance['key']),
                verify=instance['ca'],
                timeout=STAT_TIMEOUT
            )
            if rq.status_code != requests.codes.ok:
                Config.logger.error("stats failed({}): {} {}".format(rq.status_code,
                                                              instance['sensor'],
                                                              rq.text))
                continue
        except requests.exceptions.ConnectTimeout as ex:
            Config.logger.error("{}:{} Connection timeout after {} seconds".format(
                instance['host'], instance['port'], STAT_TIMEOUT))
            return "Connection Timeout"
        except requests.exceptions.ReadTimeout as ex:
            Config.logger.error("{}:{} Didn't provide stats in {} seconds".format(
                instance['host'], instance['port'], STAT_TIMEOUT))
            return "Read Timeout"
        except requests.exceptions.ConnectionError as ex:
            Config.logger.error("{}:{} Connection Error? {}".format(
                instance['host'], instance['port'], str(ex)))
            raise ex
        except requests.exceptions.SSLError as ex:
            Config.logger.error("{}:{} SSL Error - check conf {}".format(
                instance['host'], instance['port'], str(ex)))
            raise ex

        # Request Succeeded
        Config.logger.debug("response code: {}".format(rq.status_code))
        lines = rq.text.split('\n')
        data = instance.get('stats')
        for line in lines:
            if line.strip():
                k, v = line.split()
                data[k] = int(v)

        if 'oldest_timestamp' in data:
            ot = data['oldest_timestamp']
            dt = datetime.utcfromtimestamp(0) + timedelta(microseconds=ot/1000 )
            data['oldest_timestamp'] = dt.strftime(ISOFORMAT)

        if data.get('indexfile_current_reads') == 0:
            instance['idle'] = datetime.utcnow()

        datas[instance['sensor']] = data

    return datas

@celery.task(queue='query', default_retry_delay=900, max_retries=1)    # 15 minute retry delay
def query_stenographer(query_tuple, headers={}):
    """ manage the threads that query stenographer.
        Eliminate duplicate queries and ensure order
    """
    query = Query(fields=query_tuple)
    if query.invalid:
        Config.logger.error("Failed to instantiate query from {}".format(query_tuple) )
        return query.invalid

    query.progress('stenographer', 'Starting requests')
    Config.logger.debug("Process: {}".format(query.id))

    # detect duplicates, and update their timestamps to forestall deletion
    from os import mkdir
    try:
        mkdir(query.job_path, 0750)       # mkdir throws OSError if directory exists
    except OSError:
        # NOTE: python 3 throws the subclass: FileExistsError
        Config.logger.warning("duplicate query: {}".format(query.id))
        os.utime(query.job_path)
        return "Duplicate: {}".format(query.id)

    threads = []
    # Query each instance concurrently
    for instance in _INSTANCES:
        from threading import Thread
        thread = Thread(target=_requester, args=(query, instance, headers, query.job_path))
        thread.start()
        threads.append(thread)

    # Wait until all threads complete.
    alive = True
    while alive:
        alive = False
        for thread in threads:
            thread.join(1.0)
            alive = alive or thread.is_alive()

    errors = query.errors
    status = None
    if errors:
        query.error('stenographer', "stenographer queries complete", Query.FAIL)
        status = "{}: ".format(Query.FAIL) + ', '.join([ "{}:{}".format(*i) for i in errors])
    else:
        query.progress('stenographer', "stenographer queries complete", Query.SUCCESS)
        merge.apply_async(queue='io', kwargs={'query_tuple':query.tupify()})
        status = Query.SUCCESS
    query.save()
    return status

def _requester(query, instance, headers, path):
    """ Runs in the 'query' worker: performs a request against the instance
        and writes the response data to disk
    """

    query.progress(instance['sensor'], "Awaiting idle", Query.RECEIVING)
    if not _ensure_idle(instance):
        query.error(instance['sensor'], "idle timeout({})".format(QUERY_TIMEOUT), Query.FAIL)
        return

    url = "https://%s:%i/query" % (instance['host'], instance['port'])
    try:
        query.progress(instance['sensor'], "requesting {}".format(query.query), Query.RECEIVING)
        rq = requests.post(url, data=query.query, headers=headers,
                           cert=(instance['cert'], instance['key']),
                           verify=instance['ca'],
                           timeout=QUERY_TIMEOUT
                          )
        if rq.status_code == requests.codes.bad:
            error = rq.reason
            query.error(instance['sensor'], "{} {}".format(rq.status_code, error))
        elif rq.status_code == requests.codes.ok:
            query.progress(instance['sensor'], '{} bytes received'.format(len(rq.content)), Query.RECEIVED)
            out_file = join(path, "{}.pcap".format(instance['sensor']) )
            with open(out_file, 'wb') as f:
                f.write(rq.content)

    except requests.exceptions.ConnectTimeout as ex:
        query.error(instance['sensor'], "Connection Timeout({}) - {}".format(QUERY_TIMEOUT, ex) )
    except requests.exceptions.ReadTimeout as ex:
        query.error(instance['sensor'], "Data Timeout({}) - {}".format(QUERY_TIMEOUT, ex))
    except requests.exceptions.ConnectionError as ex:
        query.error(instance['sensor'], "Connection Failed - check host:port {}".format(ex))
        raise ex
    except requests.exceptions.SSLError as ex:
        query.error(instance['sensor'], "SSL Failed - check certificate config: {}".format(ex))
        raise ex
    return

def _ensure_idle(instance):
    idle = instance.get('idle')
    now = start = datetime.utcnow()
    while((IDLE_TIME     < (now - idle).total_seconds()) and
          (QUERY_TIMEOUT > (now - start).total_seconds())):
        Config.logger.info("sleeping : {}".format(instance['sensor']))
        sleep(IDLE_SLEEP)
        get_stats(selected_sensors=instance['sensor'])
        idle = instance.get('idle')
        now = datetime.utcnow()
    return (now - start).total_seconds() <= QUERY_TIMEOUT

@celery.task(queue='io', default_retry_delay=600, max_retries=1)    # 10 minute retry delay
def merge(query_tuple):
    """ Runs in the 'io' worker
        merges multiple pcap results using wireshark's mergecap tool
    """
    query = Query(fields=query_tuple)
    if not query.load():
        Config.logger.debug("DEBUG: failed to load [{}]".format(query.id))
    query.progress('merge', 'starting merge', Query.MERGE)

    files = [ join(query.job_path, f)
              for f in readdir(query.job_path, endswith='.pcap') ]
    Config.logger.debug("Merging: {}".format(','.join(files)))

    cmd = ["/usr/sbin/mergecap", "-F", "pcap", "-w", join(query.job_path, 'merged.tmp')]
    cmd.extend(files)

    from subprocess import call
    returncode = call(cmd)

    # Cleanup temporary files
    if returncode == 0:
        query.progress('merge', "merge complete, finalizing")
        # make the merged file available (rename is atomic)
        os.rename(join(query.job_path, 'merged.tmp'),
                  join(query.job_path, '{}.pcap'.format(MERGED_NAME)))
        Config.logger.debug("Removing temp files: {}".format(str(files)))
        for item in files:
            os.remove(item)
        query.complete()
    else:
        query.error('merge', "{} returned {}".format(cmd, returncode))
    query.save()
    cleanup.apply_async(queue='io')
    return returncode == 0

@celery.task(queue='io')
def cleanup(force=None):
    """ Delete queries until EXPIRE config is satisfied:
        1 - Delete anything older than EXPIRE_TIME seconds
        2 - Delete the oldest queries until we have at least EXPIRE_SPACE bytes free
    """
    period = parse_duration(Config.get('CLEANUP_PERIOD', 0))
    now = datetime.utcnow()
    global _LAST_CLEANED
    if not force and period and _LAST_CLEANED + period < now:
        Config.logger.info("Cleaned recently, aborting: {}".format(_LAST_CLEANED.strftime(Config.get('DATE_FORMAT'))))
        return

    _LAST_CLEANED = datetime.utcnow()

    from heapq import heapify, heappop

    Config.logger.info("Running Cleanup: {}".format(now.strftime(ISOFORMAT)))
    ids = Query.get_unexpired()
    ordered = [(file_modified(Query.get_job_path(i)), i) for i in ids]
    heapify(ordered)
    Config.logger.info("Cleaning: {}".format(ordered))

    if EXPIRE_TIME:
        expiring = []
        while ordered and ordered[0][0] + EXPIRE_TIME < now:
            _, i = heappop(ordered)
            expiring.append(i)
        Config.logger.info("Deleting old queries: {}".format(expiring))
        expiring = Query.expire_now(expiring)
        if expiring:
            Config.logger.error("Couldn't delete: {}".format(expiring))

    if EXPIRE_SPACE > 0:
        free_bytes = spool_space().bytes
        while ordered and free_bytes < EXPIRE_SPACE:
            _, i = heappop(ordered)
            Config.logger.info("Deleting for space: {}".format(i))
            Query.expire_now(i)
            free_bytes = spool_space().bytes
