#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sun 31 Jan 2016 09:37:54 AM CST

# File Name: docker.py
# Description: 部署docker,加载docker镜像

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("docker")
import os
from os.path import join, abspath, dirname
import StringIO
import string

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DockerModule(ModuleBase):
    NAME = 'docker'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        self.repo = kwargs.get('repo', 'https://apt.dockerproject.org/repo')
        self.images = kwargs.get('images', [])

    def __deploy__(self, context, **kwargs):
        """
            @Brief deploy
            @Param context:
            @Param **kwargs:
        """
        execute(self.install, context, hosts=self.getHostList(context))

        # 拷贝images到nfs
        nfs_module = context.module('nfs')
        if nfs_module:
            nfs_server = context.module('nfs').server
            execute(self.copyImages, context, hosts=[nfs_server.ip])

            # 加载image
            execute(self.loadImage, context, hosts=self.getHostList(context))

        return self.check(context)

    def check(self, context):
        """
            @Brief check
            @Param context:
        """
        # 检查docker是否已经安装好
        result = execute(self.checkDockerInstall,
                         hosts=self.getHostList(context))
        for res in self.resources:
            if not result.get(res.ip):
                return False

        return True

    def checkDockerInstall(self):
        """checkDocker"""
        with settings(warn_only=True):
            result = sudo('service docker status | grep running')
        return not result.failed

    def install(self, context, **kwargs):
        """
            @Brief 安装docker
            @Param context:
            @Param **kwargs:
        """
        if not context.redeploy and self.checkDockerInstall():
            return True
        # 安装bridge-utils
        sudo('apt-get install -y --force-yes -qq bridge-utils')

        # 添加gpgkey
        put(join(CURRENT_DIR, 'docker.gpg'),
            '/tmp/docker.gpg', use_sudo=True)
        sudo('apt-key add /tmp/docker.gpg')
        # 配置sources.list
        sudo(
            'echo "deb %s ubuntu-trusty main" > /etc/apt/sources.list.d/docker.list' % repo)

        with settings(warn_only=True):
            sudo('apt-get update -y -qq')

        sudo('apt-get install -y --force-yes -qq docker-engine ')

        flannel_module = context.module('flannel')
        if flannel_module and flannel_module.check(context):
            # 删除docker0
            with settings(warn_only=True):
                sudo('service docker stop')
                sudo('ip link set dev docker0 down && brctl delbr docker0')

            # 修改配置文件
            # put(join(CURRENT_DIR, 'docker.etc.default'), '/etc/default/docker', use_sudo = True)
            dns_module = context.module('dns')
            upload_template(join(CURRENT_DIR, 'docker.etc.default'), '/etc/default/docker',
                            context={'dns': dns_module.dns_server.ip}, use_sudo=True)

        # 重启docker
        sudo('service docker restart')
