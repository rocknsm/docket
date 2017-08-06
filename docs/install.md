# Docket Installation

[Back to top](README.md)

## Install

**Development Version**. We push development packages to the [Fedora COPR build service](https://copr.fedorainfracloud.org/coprs/g/rocknsm/rocknsm-2.1/). If you go to the main page, there are package repositories for both CentOS 7 and Fedora 26. (ROCK officially only supports CentOS 7, but it was easy enough to build for both platforms.

**NOTE**: If you are not running `stenographer` on this particular system, you should add the `stenographer` group. Docket assumes this group exists and controls access to the x509 keys used to authenticate to the Stenographer server.

Once you have the repo setup and the `stenographer` group, you can just do

```
# Install the packages
sudo yum install docket nginx

# Install a default nginx config for docket
sudo cp /usr/share/doc/docket-*/nginx-example.conf \
     /etc/nginx/conf.d/docket.conf

# Enable and start both nginx and docket
sudo systemctl enable nginx docket.socket
sudo systemctl restart nginx docket.socket
```

Docket does not currently have a hard dependency on `nginx` because you could feasibly use something like Apache or Lighttpd to serve this up too. If this is a default ROCK install, nginx `nginx` will already be installed.

## Configuration
Docket is configured in a simple YAML file located at
`/opt/rocknsm/docket/conf/prod.yaml`. Docket knows to read this file on startup from the `APP_CONFIG` variable stored in `/etc/sysconfig/docket`.

Now, open the `prod.yaml` file and make any necessary edits. Likely all you should change here is the `SECRET_KEY` to something random and unique per installation. See the [Flask docs](http://flask.pocoo.org/docs/0.12/api/#flask.Flask.secret_key) for more information.

_Example using `pwgen` utility_
```
sudo yum install -y pwgen
sudo sed -i "/^SECRET_KEY/s/: .*\$/: $(pwgen -s 64 1)/" \
 /opt/rocknsm/docket/conf/prod.yaml
# Stop current services and reload the socket
sudo systemctl stop docket.service
sudo systemctl restart docket.socket
```

## Verify it works
Now, you can verify it works. Most likely you have DNS running on UDP port 53 on your network. I'm assuming this is a live sensor. As such, you will _very_ likely have UDP port 53 traffic within the last 3 minutes. If all these assumptions are correct, you should see familiar `tcpdump` output with the following commands:

```
curl -s -XPOST localhost:8080/api/  \
 -d 'proto-name=udp' -d 'port=53' -d 'after-ago=3m' -v \
  | tcpdump -nr -
 ```
