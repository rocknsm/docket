# docket
A RESTful API frontend for Stenographer

Read the [documentation](docs/README.md)

## Limitations
Docket does not perform any authentication whatsoever. If
you need to control access to your PCAP data, you should
configure the forward-facing reverse proxy (such as nginx,
apache, lighttpd, etc) to perform this function. These
programs have robust and flexible methods of authentication
available from `.htpasswd` files, to PAM, to Kerberos.
