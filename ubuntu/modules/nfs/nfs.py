#!/usr/bin/env python
#coding=utf8
"""
# Author: f
# Created Time : Tue 02 Feb 2016 01:10:02 PM CST

# File Name: nfs.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("nfs")
import os
from os.path import join, abspath, dirname
import StringIO

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
            put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists
from fabric.exceptions import CommandTimeout

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
from util import retry

class NFSModule(ModuleBase):
    NAME = 'nfs'

    def __init__(self, resource_map = {}, group_map = {}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        server = kwargs.get('server')
        self.mount_dir = kwargs.get('mount_dir', '/mnt/nfsshare')
        self.data_dir = kwargs.get('data_dir', '/opt/nfsshare')
        #nfs-server的地址
        if not server:
            self.server = self.resources[0]
            LOG.warn("nfs server is not specifyed, use %s" % self.server.hostname)
        else:
            self.server = resource_map[server]

    def __deploy__(self, context, **kwargs):
        """
            @Brief __deploy__
            @Param context:
            @Param **kwargs:
        """
        execute(self.umount, context, hosts = self.getHostList(context))
        execute(self.install, context, hosts = [self.server.ip])
        execute(self.mountDir, context, hosts = self.getHostList(context))
        return self.check(context)

    def umount(self, context):
        """
            @Brief 重新部署之前将挂载的nfs目录umount
            @Param context:
        """
        mounted = self.checkMount(context)
        #如果已经mount并且必须重新部署的话,需要先umount
        if mounted and context.redeploy:
            sudo("umount %s" % self.mount_dir)

    def check(self, context):
        result = execute(self.checkServerInstall, context, hosts = [self.server.ip])
        if not result.get(self.server.ip):
            return False
        result = execute(self.checkMount, context, hosts = self.getHostList(context))
        for res in self.resources:
            if not result.get(res.ip):
                LOG.info("nfs directory is not mount on %s" % res.hostname)
                return False
        return True


    def checkServerInstall(self, context):
        """
            @Brief 检查nfsserver有没有安装好
            @Param context:
        """
        with settings(warn_only = True):
            result = sudo("service nfs-kernel-server status")
        return not result.failed

    def checkMount(self, context):
        """
            @Brief 检查nfs目录有没有挂载
            @Param context:
        """
        with settings(warn_only = True):
            result = sudo('cat /etc/mtab | grep "%s"' % self.mount_dir)
        return not result.failed

    def install(self, context):
        """
            @Brief 安装nfs server
            @Param context:
        """

        if not context.redeploy and self.checkServerInstall(context):
            LOG.info("nfs-kernel-server already deployed")
            return True
        
        with settings(warn_only = True):
            sudo("service nfs-kernel-server stop")

        #安装
        sudo("apt-get install -y --force-yes -qq nfs-kernel-server")

        #创建目录
        if not exists(self.data_dir):
            sudo("mkdir -p %s && chmod 777 %s" % (self.data_dir, self.data_dir))

        #修改exports
        append("/etc/exports", "%s *(rw,sync,no_root_squash,no_subtree_check)" % self.data_dir, use_sudo = True)

        #重启rpcbind
        with settings(warn_only = True):
            sudo("service nfs-kernel-server start")
            sudo("service rpcbind restart")

        #重启nfs server
        sudo("service nfs-kernel-server restart")

    @retry(5)
    def mountDir(self, context):
        """
            @Brief 挂载nfs目录
            @Param context:
        """
        mounted = self.checkMount(context)
        #如果已经mount并且必须重新部署的话,需要先umount
        if mounted and context.redeploy:
            sudo("umount %s" % self.mount_dir)
        if not mounted or context.redeploy:
            if not exists(self.mount_dir):
                sudo("mkdir -p %s && chmod 777 %s" % (self.mount_dir, self.mount_dir))
            with settings(warn_only = True):
                sudo("apt-get install -y --force-yes -qq nfs-common")
                try:
                    result = sudo("mount -t nfs  %s:%s %s" % (self.server.ip, self.data_dir, self.mount_dir), timeout = 10)
                except CommandTimeout, e:
                    LOG.warn('command timeout')
                    return False
                if result.failed:
                    return False
            
        append("/etc/fstab", "%s:%s %s nfs rw 0 0" % (self.server.ip, self.data_dir, self.mount_dir), use_sudo = True)
        return True





