# Docket design

[Back to top](README.md)

Docket uses the [Flask](http://flask.pocoo.org/) framework and several
extensions to provide a REST-ful interface for Stenographer. 

Queries are enqueued by a simple request such as:
dockethost:8080/q/host/1.2.3.4/port/80/after/5m

docket responds with JSON encoded metadata:
{
    "Requested": "2018010T22:11:40",
    "id": "10a53543eb90f99251add6c9d5dd664c",
    "query": "port 21 and after 2018-01-10T22:10:00Z and before 2018-01-10T22:12:00Z",
    "url": "/10a53543eb90f99251add6c9d5dd664c/merged.pcap"
}

The status of that request can then be queried:

dockethost:8080/status/10a53543eb90f99251add6c9d5dd664c
{"10a53543eb90f99251add6c9d5dd664c": { "events": [...], "requests": {...}, "state": "Completed" }}

and retrieved
dockethost:8080/10a53543eb90f99251add6c9d5dd664c/merged.pcap

ROCK NSM presents network data from Bro and Suricata (by default) in a
web-driven analysis interface called Kibana. The goal is to provide the analyst
a seamless workflow to retrieve the PCAP from this interface. We're not quite
there yet, but we now have the functional backend to make it happen!

## Overview ##
Requests are parsed, deduplicated (same clauses, similar timeframe), and queued.
Docket responds with an identifier that can be provided to Docket APIs for additional info.

The query (Celery FIFO) is processed sequentially in the Celery 'queue' worker process.
The query worker makes concurrent requests from all instances and writes the results to the **SPOOL_DIR** directory. 
Once all concurrent requests are complete a 'merge' operation is queued for the 'io' worker and the 'query' worker starts the next request.

The 'io' worker (Celery FIFO) merges captures into a single **MERGED_NAME**.pcap
To do so it runs wireshark's "mergecap" tool.
After merging is complete, the source files are deleted and the result is made available (renamed .tmp->.pcap) as a static file.

## Query / QueryRequest ##
A Query object is built to make and track query requests.
Each request is parsed into a list of standardized clauses which are then used to build the final query string.
Deduplication is acheived by hashing query strings, as clauses are order independant and timing is discrete.
Unless specified in the request, a Query has a start time of 24 hours ago, and an end time of 'the end of the current TIME_WINDOW'.

## Stenographer Queries ##

The 'query' Celery worker handles all queries to the stenographer instances. 
This is to minimize thrashing (platter heads, caches, etc).
A directory (SPOOL_DIR/ID) is created, or if it exists the query is abandoned duplicate.

Python threads are created for each stenographer instance and the 'Requests' module retreives the packet data while managing error conditions (timeouts).
Each completed result is then written into the directory as 'MERGED_NAME.pcap' .
The worker waits (passively) for all 'Requests' to complete. 
Timeouts (QUERY_TIMEOUT) are logged, and a 'merge' is queued.

## IO ##

The 'io' Celery worker handles merge operations and cleanup. 
Again a single process reduces thrashing.

## Cleaning ##
Cleanup is triggered by every query, but it immediately aborts unless it has been at least CLEANUP_TIME since last run.
Cleanup deletes query directories older than EXPIRE_TIME, and ensures EXPIRE_SPACE on SPOOL_DIR's filesystem.

## API ##

### /status
Status provides a current state and complete history of each query in JSON form.
The current state of each stenographer request is also listed to aid in checking for stenographer problems (timeout, misconfiguration, etc).

### /stats
Stats for each stenographer instance are maintained by the 'query' worker process to ensure 'idleness' before making a stenographer API request.
Stats requested through the API are performed immediately (by the uwsgi 'webserver' process) and returned.
Free space and free nodes of the SPOOL_DIR is also reported.

### /ids
a list of valid Query IDs
Essentially a directory read on the **SPOOL_DIR** in the uwsgi process.
If a id (or a comma separated list of ids) is provided then the returned list will be filtered by the submitted ids.

### /urls
A dictionary or {id: URL} for available merged capture files is provided.
If a id (or a comma separated list of ids) is provided then the returned list will be filtered by the submitted ids.

## Configuration: ##
All configuration options are described in conf/prod.yaml
