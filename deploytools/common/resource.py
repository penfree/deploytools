#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 08:26:00 AM CST

# File Name: resource.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


class Resource(object):
    '''
        硬件资源描述
    '''

    def __init__(self, name, hostname, ip, **kwargs):
        self.name = name
        self.hostname = hostname
        self.ip = ip
        for k, v in kwargs:
            setattr(self, k, v)
