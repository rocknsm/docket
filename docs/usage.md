# Usage

[Back to top](README.md)

**Table of Contents**
- [GET queries](#get)
- [POST queries](#post)
- [Sensor Stats](#stats)

<a name="get" />
## HTTP GET URI-based query
If you want to generate links to facilitate "click-to-PCAP" functionality or you
just want shorthand usage with curl, this is the interface for you. Docket
supports arbitrary GET queries using following translations to the Stenographer
API. All terms are AND'd together to refine the query. The API does not
currently support OR semantics. Time intervals may be expressed with any
combination of: h or m
Note that `host`, `net`, and `port` accept one or two values, as shown.

The API endpoint here is `/pcap/` followed by the URI
 queries listed below.

```
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
```

#### Example query using curl
```
$ curl -s localhost:8080/pcap/host/192.168.254.201/port/53/udp/after/3m/ | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
```

<a name="post" />
## POST Query API

If you're developing web forms like the provided one or interacting via a web
service, this is probably how you want to interact with Docket. It supports the
following query terms translated to stenographer API. All terms are AND'd
together to refine the query. The API does not currently support OR semantics.
Time intervals may be expressed with any combination of: h or m.

See below for examples.

### Summary

If you're already familiar with the Stenographer API, here's how you can
translate HTTP POST form-encoded fields to generate queries. `host`, `net`, and
`port` accept one or two values, as shown.

```
host=1.2.3.4 -> 'host 1.2.3.4'
host=1.2.3.4, host=4.5.6.7 -> 'host 1.2.3.4 and host 4.5.6.7'
net=1.2.3.0/24 -> 'net 1.2.3.0/24'
port=80 -> 'port 80'
proto=6 -> 'ip proto 6'
proto-name=tcp -> 'tcp'
proto-name=tcp, port=80 -> 'tcp and port 80'
before=2017-04-30T00:00:00Z -> 'before 2017-04-30T00:00:00Z'
after=2017-04-30T13:26:43Z -> 'after 2017-04-30T13:26:43Z'
before-ago=45m -> 'before 45m ago'
after-ago=3h -> 'after 180m ago'
after-ago=3h30 -> 'after 210m ago'
after-ago=3.5h -> 'after 210m ago'
```

### POST Examples

#### Example query using curl (form-encoded):
```
$ curl -s -XPOST localhost:8080/api/ -d 'host=192.168.254.201' -d 'proto-name=udp' -d 'port=53' -d 'after-ago=3m' | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
```
#### Example query using curl (json-encoded):

This interface also supports JSON-encoded queries (requires content-type header)

```
curl -s -XPOST localhost:8080/api/ -H 'Content-Type: application/json' -d '
{ "host": "192.168.254.201", "proto-name": "udp", "port": 53, "after-ago": "3m" }' | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
16:16:32.700658 IP 192.168.254.201.50169 > 205.251.195.137.domain: 27094% [1au] A? ping.example.net. (47)
16:16:32.759907 IP 205.251.195.137.domain > 192.168.254.201.50169: 27094*- 8/4/1 A 198.18.209.234, A 198.18.232.30, ...
```

<a name="stats" />
## HTTP Stats Interface

Finally, Docket exposes the stats API of Stenographer. This
is helpful to get some metadata about the health of each
configured sensor, such as the oldest PCAP on disk, how many
files are currently on disk, and how many files have aged
off. This information is returned in a JSON array of
responses from each sensor.

#### Example curl stats query

Here's some example output of this query endpoint. Note the
displayed `sensor` is the name given in the Docket
configuration file located at `/opt/rocknsm/docket/conf/prod.yaml`.

```
curl localhost:8080/stats/
[
  {
    "aged_files": 4143,
    "current_files": 6088,
    "http_request_query_POST_bytes": 1317598292,
    "http_request_query_POST_completed": 109,
    "http_request_query_POST_nanos": 477279214677,
    "index_base_lookup_nanos": 550931912435,
    "index_base_lookups_finished": 1430455,
    "index_base_lookups_started": 1430455,
    "index_set_lookup_nanos": 1640072170260,
    "index_set_lookups_finished": 1057051,
    "index_set_lookups_started": 1057051,
    "indexfile_current_reads": 0,
    "indexfile_read_nanos": 542332051007,
    "indexfile_reads": 1096635,
    "oldest_timestamp": "2017-08-01T20:17:00.114446Z",
    "packet_read_nanos": 534748866220,
    "packet_scan_nanos": 0,
    "packets_blocks_read": 0,
    "packets_read": 7954960,
    "packets_scanned": 0,
    "removed_hidden_files": 1,
    "removed_mismatched_files": 0,
    "sensor": "sensor-001"
  }
]
```
