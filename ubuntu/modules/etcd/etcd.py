#!/usr/bin/env python
#coding=utf8
"""
# Author: f
# Created Time : Sat 30 Jan 2016 06:09:31 PM CST

# File Name: etcd.py
# Description: 部署etcd

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("etcd")
import json
import os
from os.path import join, abspath, dirname
import StringIO

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
            put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists
from util import retry

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

class EtcdModule(ModuleBase):
    NAME = 'etcd'

    def __init__(self, resource_map = {}, group_map = {}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        self.cluster = kwargs.get('cluster', 'bdmd-etcd')
        self.datadir = kwargs.get('datadir', '/var/lib/etcd')
        self.logdir = kwargs.get('logdir', '/var/log/etcd')

    def getDnsRecord(self, context):
        """
            @Brief getDnsRecord
                    获取etcd的dns SRV记录, dns-server的部署模块会调用此方法获取需要添加的记录并完成配置
            @Param context:
        """
        records = []
        for res in self.resources:
            records.append('_etcd-server._tcp.%s. 300 IN SRV 0 0 2380 %s.' % (context.domain, res.hostname))
        return records


    def __deploy__(self, context, **kwargs):
        """
            @Brief deploy
                在部署etcd之前一定要在dns中配置好服务发现,使用oneclick工具部署,则会自动配置,
                如果不使用oneclick工具部署dns-server,则需要手动添加dns记录
            @Param context:
            @Param **kwargs:
        """
        #安装etcd
        execute(self.install, context, hosts = self.getHostList(context))

        #返回安装结果
        return self.check(context)

    @retry(5)
    def check(self, context):
        """
            @Brief 检查etcd是否正常启动
            @Param context:
        """
        with settings(warn_only = True):
            result = local("curl -L http://%s:2380/members" % (self.resources[0].hostname), capture=True)
        if result.failed:
            return False
        #检查是否所有的节点都已经加入集群了
        try:
            obj = json.loads(result.stdout)
            members = [item['name'] for item in obj if item.get('name')]
            print members
            for res in self.resources:
                if res.hostname not in members:
                    LOG.error('etcd on [%s] deployed failed' % res.hostname)
                    return False
        except Exception,e:
            LOG.exception(e)
            LOG.error('etcd cluster deploy failed')
            return False
        return True

    def install(self, context):
        """
            @Brief 安装etcd
            @Param context:
        """
        #安装supervisor
        sudo("apt-get install -y --force-yes -qq supervisor")
        #创建用户
        with settings(warn_only = True):
            sudo("useradd etcd")

        #创建目录
        sudo("mkdir -p /opt/ && mkdir -p %(datadir)s && mkdir -p %(logdir)s" % \
                {"datadir" : self.datadir, "logdir" : self.logdir})

        #通过压缩包安装etcd
        put(join(CURRENT_DIR, "etcd.tgz"), "/tmp/etcd.tgz", use_sudo = True)
        sudo("tar -xzf /tmp/etcd.tgz -C /opt/")
        put(join(CURRENT_DIR, "start.py"), "/opt/etcd/start.py", use_sudo = True, mode = "0755")

        #修改目录权限
        sudo("chown etcd:etcd -R /opt/etcd && chown etcd:etcd -R %(datadir)s && chown etcd:etcd -R %(logdir)s" % \
                {"datadir" : self.datadir, "logdir" : self.logdir})

        #上传supervisor配置
        upload_template(os.path.join(CURRENT_DIR, 'etcd.conf.template'), '/etc/supervisor/conf.d/etcd.conf', 
                context = {'domain' : context.domain, 'datadir' : self.datadir, 'logdir' : self.logdir, 'cluster' : self.cluster},
                            use_sudo = True)
        #update supervisor
        sudo("supervisorctl update")
        sudo('supervisorctl restart etcd')


