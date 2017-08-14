# Hacking on Docket

[Back to top](README.md)

If you want to hack on docket, this is the process we use for building and testing our RPMs.

## Building

To build, you need to install `mock` and `tito`. These are both available in
EPEL. I do my builds in a vagrant CentOS 7.3 machine. You can prep with:

```
sudo yum install -y epel-release && sudo yum install -y mock tito
```

Then, to build the most recent tagged commit, do the following to produce build
artifacts in the `./build` directory.

```
tito build --rpm --builder=mock --arg mock=epel-7-x86_64 -o ./build
```

To build from the most recent commit, use the following instead.
```
tito build --test --rpm --builder=mock --arg mock=epel-7-x86_64 -o ./build
```
