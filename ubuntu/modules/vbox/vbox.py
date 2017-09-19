#!/usr/bin/env python
#coding=utf8
"""
# Author: f
# Created Time : Mon 18 Jan 2016 02:17:29 PM CST

# File Name: vbox.py
# Description:

1. 安装virtualbox
2. 加载虚拟机, 由于虚拟机文件通常很大,因此加载虚拟机只允许在部署脚本所在机器上进行

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("vbox")
import os
import StringIO
from util import retry

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
            put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment
from os.path import join, abspath, dirname

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
import socket

class VirtualMachine(object):
    #虚拟机配置
    def __init__(self, name, vrdeport, vm_dir, memory = 256, cpu = 1,
                        share_host_path = None, sharefolder = None):
        #虚拟机名称
        self.name = name
        #vrde端口号
        self.vrdeport = vrdeport
        #内存,单位是MB
        self.memory = memory
        #cpu数目
        self.cpu = cpu
        #共享目录名称
        self.sharefolder = sharefolder
        #共享目录的宿主机路径
        self.share_host_path = share_host_path
        self.vm_dir = vm_dir

class VboxModule(ModuleBase):
    NAME = 'vbox'

    def __init__(self, resource_map = {}, group_map = {}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        #debian repo
        self.repo = kwargs.get('repo', 'http://download.virtualbox.org/virtualbox/debian')
        #虚拟机存放目录
        self.data_dir = kwargs.get('data_dir', "/root/vbox")
        #要加载的虚拟机
        self.vms = []
        for vm in kwargs.get('vms', []):
            self.vms.append(VirtualMachine(**vm))
        #待部署的机器
        self.vbox_server = self.resources[0]

    def bashDataDir(self):
        '''
            路径中带空格时bash需要加斜杠转义
        '''
        if ' ' not in self.data_dir:
            return self.data_dir
        else:
            return self.data_dir.replace(' ', '\\ ')

    def check(self, context):
        """
            @Brief check
            @Param context:
        """
        result = execute(self.checkVbox, hosts = [self.vbox_server.ip])
        return result.get(self.vbox_server.ip)

    def checkVbox(self):
        """checkVbox"""
        with settings(warn_only = True):
           result = sudo('vboxmanage --version')
        return not result.failed

    def __deploy__(self, context, **kwargs):
        '''

        '''
        logging.info("Installing virtual box")
        execute(self.install, context, hosts = self.getHostList(context))

        #try load vms
        curr_hostname = socket.getfqdn()
        if curr_hostname != self.vbox_server.hostname:
            LOG.warn("vm can only be load on local machine")
            return True
        
        for vm in self.vms:
            LOG.info("Begin to load [%s]" % vm.name)
            with settings(warn_only = True):
                ret = local("vboxmanage showvminfo %s" % vm.name)
                if not ret.failed:
                    LOG.warn("vm[%s] already exists, skiped" % vm.name)
                    continue
            vm_dir = vm.vm_dir

            LOG.info("Copying files to [%s]" % self.data_dir)
            local("mkdir -p %s && cp -rf %s %s" % (self.bashDataDir(), vm_dir, join(self.bashDataDir(), vm.name)))
            LOG.info("Register vm [%s]" % vm.name)
            with settings(warn_only = True):
                ret = local("vboxmanage registervm %s" % join(self.bashDataDir(), vm.name, '%s.vbox' % vm.name))
                if ret.failed:
                    LOG.error("register vm[%s] failed" % vm.name)
                    continue

                ret = local("vboxmanage modifyvm %s --vrde on" % vm.name)
                if ret.failed:
                    LOG.error("turn on vrde failed")
                    continue

                ret = local("vboxmanage modifyvm %s --vrdeport %s" % (vm.name, vm.vrdeport))
                if ret.failed:
                    LOG.error("set vrdeport to [%s] failed" % vm.vrdeport)
                    continue

                ret = local("vboxmanage modifyvm %s --memory %s" % (vm.name, vm.memory))
                if ret.failed:
                    LOG.error("set vm[%s] memory to [%s]MB" % (vm.name, vm.memory))
                    continue

                ret = local("vboxmanage modifyvm %s --cpus %s" % (vm.name, vm.cpu))
                if ret.failed:
                    LOG.error("set vm[%s] cpu number to [%s]" % (vm.name, vm.cpu))
                    continue

                if vm.sharefolder and vm.share_host_path:
                    if not os.path.exists(vm.share_host_path):
                        local("mkdir -p %s; chmod 755 %s" % (vm.share_host_path, vm.share_host_path))
                    ret = local('vboxmanage sharedfolder add %s --name "%s" --hostpath %s --transient' % \
                                    (vm.name, vm.sharefolder, vm.share_host_path))
                    if ret.failed:
                        LOG.error("mount sharefolder failed")
                        continue

        return True

    def install(self, context):
        '''
            安装virtualbox
        '''
        repo_module = context.module('debian-repo')
        if not context.offline or not repo_module.use_local_file_repo:
            repo = 'deb %s trusty contrib' % self.repo
            append("/etc/apt/sources.list.d/vbox.list", repo, use_sudo = True)
        

        put(join(CURRENT_DIR, 'oracle_vbox.asc'), "/tmp/oracle_vbox.asc", use_sudo = True)
        sudo("cat /tmp/oracle_vbox.asc | apt-key add -")
        sudo("rm -rf /tmp/oracle_vbox.asc")
        with settings(warn_only = True):
            sudo("apt-get update -qq")
        sudo("apt-get install -y --force-yes -qq virtualbox-5.0 dkms")
        put(join(CURRENT_DIR, "Oracle_VM_VirtualBox_Extension_Pack-5.0.16-105871.vbox-extpack"), "/tmp/Oracle_VM_VirtualBox_Extension_Pack-5.0.16-105871.vbox-extpack", use_sudo = True)
        with settings(warn_only = True):
            sudo("vboxmanage extpack install /tmp/Oracle_VM_VirtualBox_Extension_Pack-5.0.16-105871.vbox-extpack")
        return True


