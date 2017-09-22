#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 08:46:59 AM CST

# File Name: resgroup.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger('resgroup')


class ResourceGroup(object):
    '''
        资源组
    '''

    def __init__(self, name, resources, resource_map):
        self.name = name
        self.resources = []
        if resources:
            for res in resources:
                if res not in resource_map:
                    raise ValueError('resource[%s] is not defined' % res)
                else:
                    self.resources.append(resource_map[res])
