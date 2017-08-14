# Docket design

[Back to top](README.md)

Docket uses the [Flask](http://flask.pocoo.org/) framework and several
extensions to provide a REST-ful interface for Stenographer. The primary
motivation was to create a "click-to-PCAP" interface for ROCK NSM. Stenographer
does an amazing job of capturing packets at extremely high speed and efficiency
and indexing them for rapid retrieval. It automatically manage disk space
utilization. On top of all of this, it provides a handy wrapper around `curl`
to retrieve the packets.

All of that is well and good, except new analysts may not be as familiar with
connecting to the sensor they want over SSH, running `stenoread`, filtering
with BPF, and finally pulling the PCAP back for analysis. And beyond familiarity
if we can streamline that process, why wouldn't we? ;)

ROCK NSM presents network data from Bro and Suricata (by default) in a
web-driven analysis interface called Kibana. The goal is to provide the analyst
a seamless workflow to retrieve the PCAP from this interface. We're not quite
there yet, but we now have the functional backend to make it happen!
