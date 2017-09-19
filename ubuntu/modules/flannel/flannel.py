#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 30 Jan 2016 09:23:31 PM CST

# File Name: flannel.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("flannel")
import os
import StringIO

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists
from util import retry
from os.path import join, abspath, dirname

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class FlannelModule(ModuleBase):
    NAME = 'flannel'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        self.network = kwargs.get('network', '172.16.0.0/16')
        self.logdir = kwargs.get('logdir', '/var/log/flannel')
        # etcd地址,若不写则尝试从etcd模块获取,如果获取不到则部署失败
        self.etcd_host = kwargs.get('etcd_host')

    def __deploy__(self, context, **kwargs):
        """
            @Brief deploy
            @Param context:
            @Param **kwargs:
        """
        # 安装flannel
        execute(self.install, context, hosts=self.getHostList(context))
        return self.check(context)

    def check(self, context):
        # 检查是否安装成功
        result = execute(self.checkStatus, context,
                         hosts=self.getHostList(context))
        for res in self.resources:
            if not result.get(res.ip):
                LOG.warn("flannel is not started on %s" % res.hostname)
                return False
        return True

    @retry(3)
    def checkStatus(self, context):
        """
            @Brief 检查flannel是否已经安装成功
            @Param context:
        """
        with settings(warn_only=True):
            result = sudo('ifconfig | grep flannel')
        if result.failed:
            time.sleep(3)
            return False
        return True

    def install(self, context):
        """
            @Brief 安装flannel
            @Param context:
        """
        # 确保supervisor已经安装
        sudo('apt-get install -y --force-yes -qq supervisor')

        # 向etcd写入flannel的配置
        etcd_host = self.etcd_host
        if not etcd_host:
            etcd_module = context.module('etcd')
            if not etcd_module:
                raise ValueError('etcd_module not found')
            etcd_host = etcd_module.resources[0].hostname
        result = local(
            "curl -X PUT http://%s:2379/v2/keys/coreos.com/network/config -d value='{ \"Network\": \"%s\" }'" % (etcd_host, self.network))

        # 创建目录
        sudo('mkdir -p /opt/ && mkdir -p %s' % self.logdir)

        # 上传安装包
        put(join(CURRENT_DIR, 'flannel.tgz'), '/tmp/flannel.tgz', use_sudo=True)
        sudo('tar -xzf /tmp/flannel.tgz -C /opt/')

        # 配置supervisor
        endpoint = ','.join(
            ['http://%s:2379' % res.hostname for res in context.module('etcd').resources])

        upload_template(os.path.join(CURRENT_DIR, 'flannel.conf.template'), '/etc/supervisor/conf.d/flannel.conf',
                        context={'endpoint': endpoint},
                        use_sudo=True)
        sudo("supervisorctl update")
