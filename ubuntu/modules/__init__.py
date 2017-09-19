#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 05:20:20 PM CST

# File Name: __init__.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from dns.dns import DNSModule
from basic.basic import BasicModule
from testmodule.testmodule import TestModule
from vbox.vbox import VboxModule
from etcd.etcd import EtcdModule
from flannel.flannel import FlannelModule
from docker.docker import DockerModule

NAME2MODULE = {
    'testmodule': TestModule,
    'basic': BasicModule,
    'dns-server': DNSModule,
    'vbox': VboxModule,
    'etcd': EtcdModule,
    'flannel': FlannelModule,
    'docker': DockerModule,
}
