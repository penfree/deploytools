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
#from basic.basic import BasicModule
from testmodule.testmodule import TestModule
from cbasic.basic import CentosBasicModule
from openvpn.openvpn import OpenvpnModule

NAME2MODULE = {
    'testmodule': TestModule,
    'openvpn': OpenvpnModule,
    #'basic': BasicModule,
    'dns-server': DNSModule,
    'cbasic': CentosBasicModule,
}
