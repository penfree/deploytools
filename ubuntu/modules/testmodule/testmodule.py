#!/usr/bin/env python
#coding=utf8
"""
# Author: f
# Created Time : Mon 18 Jan 2016 01:32:28 PM CST

# File Name: testmodule.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("testmodule")
import os
import StringIO
from util import retry

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
            put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

class TestModule(ModuleBase):
    NAME = 'testmodule'

    def __init__(self, resource_map = {}, group_map = {}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)


    def deploy(self, context, **kwargs):
        '''
            测试模块
        '''
        execute(self.test, hosts = self.getHostList(context))
        return True

    @retry(3)
    def test(self):
        '''
            执行测试任务
        '''
        sudo("hostname -f")
        return False
