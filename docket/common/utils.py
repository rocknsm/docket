##
## Copyright (c) 2017, 2018 RockNSM.
##
## This file is part of RockNSM
## (see http://rocknsm.io).
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
##
from werkzeug.exceptions import BadRequest
from datetime import datetime, timedelta
from fcntl import flock, LOCK_EX, LOCK_NB
from collections import OrderedDict, Mapping, namedtuple
from socket import inet_pton, AF_INET6, AF_INET, error as SocketError
from flask import request, has_request_context
import os
import yaml
import re

# import docket configuration
from config import Config

FreeSpace = namedtuple('FreeSpace', ['bytes', 'nodes'] )
ISOFORMAT = '%Y-%m-%dT%H:%M:%SZ'

try:
    basestring
    def is_str(s):
        return isinstance(s, basestring)
except NameError:
    def is_str(s):
        return isinstance(s, str)


DURATIONS= {'US': 0.000001,
            'MS': 0.001,
            'S' : 1,
            'M' : 60,
            'H' : 60*60,
            'D' : 60*60*24,
            'W' : 60*60*24*7, }
RX_DURATION = re.compile(r'|'.join([r'(?:(?P<{}>[\d.]+)\s*'
                                    r'(?:{}|{}))'.format(k, k, k.lower())
                                    for k,v in DURATIONS.items()]))
def parse_duration(s):
    total = 0
    if type(s) in (int, float):
        total, s = s, ''
    elif not is_str(s):
        return None
    try:
        for it in RX_DURATION.finditer(s):
            for k,v in it.groupdict().items():
                if v:
                    total += DURATIONS[k] * float(v)
        return timedelta(seconds=total or float(s))
    except ValueError:
        return None


CAPACITIES = {'B': 1,
              'KB':1024,
              'MB':1024**2,
              'GB':1024**3,
              'TB':1024**4,
              'PB':1024**5, }
RX_CAPACITY = re.compile(r'|'.join([r'(?:(?P<{}>[\d.]+)\s*'
                                    r'(?:{}|{}))'.format(k, k, k.lower())
                                    for k,v in CAPACITIES.items()]))
def parse_capacity(s):
    total = 0
    if type(s) in (int, float):
        return int(s)
    elif not is_str(s):
        return None
    for it in RX_CAPACITY.finditer(s):
        for k,v in it.groupdict().items():
            if v:
                total += CAPACITIES[k] * float(v)
    return total or int(s)

def epoch(when):
    return int((when - datetime(1970,1,1)).total_seconds())

def from_epoch(epoch):
    return datetime(1970,1,1) + timedelta(seconds=epoch)

def readdir(path, startswith=None, endswith=None):
    files = []
    for i in os.listdir(path):
        if i[0] == '.':
            continue
        if endswith and not i.endswith(endswith):
            continue
        if startswith and not i.startswith(startswith):
            continue
        file_path = os.path.join(path, i)
        stats = os.stat(file_path)
        if stats.st_size < 1:
            continue
        files.append(i)
    return files

def file_modified(path, format=None):
    """ return the modified datetime of the file at path
        if format is specified - use strftime and return a string instead
    """
    t = from_epoch(os.path.getmtime(path))
    if format:
        return t.strftime(format)
    return t

def is_sequence(arg):
    return not is_str(arg) and (
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

def recurse_update(a, b, ignore_none = False):
    """ add everything in b to a
        _overwrites_ existing values unless the new value is None and ignore_none is True
        you might think deepcopy for this, but it can't merge two dictionaries
    """
    for key,bVal in b.items():
        if isinstance(bVal, Mapping):
            if (ignore_none):
                a[key] = recurse_update(a.get(key, {}), {k:v for k,v in bVal.items() if v}, True)
            else:
                a[key] = recurse_update(a.get(key, {}), bVal)
        elif is_sequence(bVal):
            if not is_sequence(a[key]):
                a[key] = bVal if a[key] in bVal else bVal.append(a[key])
            else:
                a[key].extend([v for v in bVal if v not in a[key] ])
        else:
            a[key] = bVal if bVal or not ignore_none else a[key]
    return a

def file_lock(f, timeout=2):
    """ True if f was locked, False otherwise """
    giveUp = datetime.utcnow() + timedelta(seconds=timeout)
    while datetime.utcnow() < giveUp:
        try:
            flock(f, LOCK_EX | LOCK_NB)
            return True
        except IOError as e:
            if e.errno == errno.EAGAIN:
                time.sleep(0.1)
    return False

def update_yaml(path, val = None):
    """ given a path to a yaml file:
            if val: update val from the file, update the file, and return val.
            else:   load the file and return that.
        returns
            False - locking failed, no update occurred
            new value - File data, updated with provided value
    """
    if not path:
        return False
    locked = False

    with open(path, 'a+b') as f:
        if not file_lock(f, timeout=Config.get("LOCK_TIMEOUT", 2)):
            Config.logger.error("Failed to lock {}".format(path))
            return False

        f.seek(0)
        data = f.read()
        if len(data):
            tmp = yaml.load(data)
            if not val:
                Config.logger.debug("loaded {}".format(path))
                # No changes to write.
                return tmp
            elif hasattr(tmp, 'update'):
                Config.logger.debug("{}.update( {} )".format(tmp,val))
                tmp.update(val)
            elif hasattr(val, '__add__'):
                Config.logger.debug("{} += {}".format(val,tmp))
                val += tmp
            else:
                Config.logger.error("loaded {}, can't update {}".format(path,val))
                return val

        f.seek(0)
        f.truncate()
        f.write(yaml.dump(val))
    return val

def write_yaml(path, val):
    """ Once a file lock is obtained, path is overwritten with yaml encoded contents of val
    """
    if not path or val is None:
        return False
    # Even though we're just 'writing' the file, I don't want to clobber it until I get a lock
    # so I open it for append
    with open(path, 'a+b') as f:
        if not file_lock(f, timeout=Config.get("LOCK_TIMEOUT", 2)):
            Config.logger.error("Failed to lock {}".format(path))
            return False

        f.seek(0)
        f.truncate()
        f.write(yaml.dump(val))
        return True

def free_space(f):
    """ return ( Bytes Free, Nodes free ) for the filesystem containing the provided file
        ex: free_space( open( '/tmp/nonexistant', 'w' ) ) -> ( bytes=123456789 , nodes=1234 )
    """
    vfs = os.fstatvfs(f.fileno())
    return FreeSpace(bytes = vfs.f_bavail * vfs.f_frsize, nodes = vfs.f_favail)

def spool_space():
    """ return free space in SPOOL_DIR """
    fn = os.path.join( Config.get('SPOOL_DIR'), 'docket.yaml' )
    with open(fn, 'a+b') as f:
        return free_space(f)

def space_low():
    space = spool_space()
    if space.bytes < parse_capacity(Config.get('FREE_BYTES', '100MB')):
        return "Low on disk space: {} free".format(space.bytes)
    if space.nodes < Config.get('FREE_NODES', 100 ):
        return "Low on FileSystem Nodes: {} free".format(space.nodes)
    return False

def validate_ip(ip):
    """ return a tuple (string, AF_INET) for valid IP addresses
        raise an exception for bad addresses
    """
    try:
        if len(ip) > 51:
            raise BadRequest("Unable to parse ip: {}".format(ip))
            #raise ValueError("Invalid IP provided: %50s" % (ip))
        version = AF_INET
        if ip.find(':') >= 0:
            version = AF_INET6
        inet_pton(version, ip)
    except SocketError:
        raise BadRequest("Unable to parse ip: {}".format(ip))
        #raise ValueError("Invalid IP provided: {}".format(ip))
    return (ip, version)

def validate_net(cidr):
    """ return a tuple (string, AF_INET) for 'IP/cidr' strings
        raise an exception if input is invalid
    """
    if not '/' in cidr:
        raise ValueError("Invalid net: {} Expects a CIDR IP/mask".format(cidr))

    ip, net = cidr.split('/')
    ip, version = validate_ip(ip)
    if version == AF_INET:
        count = 0
        for i in net.split('.'):
            if 0 <= int(i) < 256:
                count += 1
        if count == 1 and int(i) <= 32:
            return (cidr, version)
        if count == 4:
            return (cidr, version)
        raise ValueError("Invalid IPv4 netmask {}".format(net))
    elif not (re.match(r'\d+', net) and int(net) < 128):
        raise ValueError("Invalid IPv6 netmask: {}".format(net))
    return (cidr, version)

def md5(val):
    from hashlib import md5
    m = md5()
    m.update(val)
    return m.hexdigest()

def sha256(val):
    from hashlib import sha256
    m = sha256()
    m.update(val)
    return m.hexdigest()
