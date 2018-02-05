
# Usage

[Back to top](README.md)

**Table of Contents**
- [GET-style queries](#http-get-uri-based-query)
- [POST queries](#post-query-api) (form or json encoded)
- [Sensor Stats](#http-stats-interface)
- [stenoread compatibility](#stenoread-compatibility)

## HTTP GET URI-based query

If you want to generate links to facilitate "click-to-PCAP" functionality or you
just want shorthand usage with curl, this is the interface for you. Docket
supports arbitrary GET queries using following translations to the Stenographer
API. All terms are AND'd together to refine the query. The API does not
currently support OR semantics. Time intervals may be expressed with any
combination of: [ us: microseconds, ms: milliseconds, s: seconds, m: minutes, h: hours, d: days, w:weeks ]
Note that `host`, `net`, and `port` accept one or two values, as shown.

The API endpoint here is `/uri/` followed by the URI
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
$ curl -s localhost:8080/uri/host/192.168.254.201/port/53/udp/after/3m/ | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
```

## POST Query API

<a name="post" />
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
$ curl -s -XPOST localhost:8080/ -d 'host=192.168.254.201' -d 'proto-name=udp' -d 'port=53' -d 'after-ago=3m' | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
15:38:00.311222 IP 192.168.254.201.31176 > 205.251.197.49.domain: 52414% [1au] A? ping.example.net. (47)
15:38:00.345042 IP 205.251.197.49.domain > 192.168.254.201.31176: 52414*- 8/4/1 A 198.18.249.85, A 198.18.163.178, ...
```
#### Example query using curl (json-encoded):

This interface also supports JSON-encoded queries (requires content-type header)

```
curl -s -XPOST localhost:8080/ -H 'Content-Type: application/json' -d '
{ "host": "192.168.254.201", "proto-name": "udp", "port": 53, "after-ago": "3m" }' | tcpdump -nr -
reading from file -, link-type EN10MB (Ethernet)
16:16:32.700658 IP 192.168.254.201.50169 > 205.251.195.137.domain: 27094% [1au] A? ping.example.net. (47)
16:16:32.759907 IP 205.251.195.137.domain > 192.168.254.201.50169: 27094*- 8/4/1 A 198.18.209.234, A 198.18.232.30, ...
```


## HTTP Stats Interface

<a name="stats" />
Finally, Docket exposes the stats API of Stenographer. This
is helpful to get some metadata about the health of each
configured sensor, such as the oldest PCAP on disk, how many
files are currently on disk, and how many files have aged
off. This information is returned in a JSON array of
responses from each sensor.

#### Example curl stats query

Here's some example output of this query endpoint. Note the
displayed `sensor` is the name given in the Docket
configuration file located at `/etc/docket/prod.yaml`.

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

## Stenoread compatibility

As a final note, the very first interface to Docket that we developed was to
make it compatible with the current `stenoread` query interface. This made it
easier to test development and as a side effect, allowed stenoread to query
multiple backend hosts. Unfortunately, Docket doesn't currently run over TLS,
so you have to do some wizardry with the nginx front-end to provide the TLS
layer. In a future release, perhaps we can make this more seamless, but if you
wanted to use this I wanted to note the high-level things to do. Currently the
details are left as an exercise to the reader.

1. Modify `/etc/stenographer/config` on the system running `stenoread` to point
to the host and port Docket is running on.
2. Configure TLS in nginx using a server cert signed by the same CA that the
Stenographer client cert uses.
3. Accept client cert authentication in nginx.
4. ...
5. Profit! and run queries via the `/query` API!
