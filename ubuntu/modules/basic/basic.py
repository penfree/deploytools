#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Mon 18 Jan 2016 11:47:53 AM CST

# File Name: basic.py
# Description:  机器的基本软件包安装和配置

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
LOG = logging.getLogger("basic")
import os
from os.path import join
import StringIO

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, contains
from util import retry
import yaml

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class BasicModule(ModuleBase):
    NAME = 'basic'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        # 需要安装的debian包
        self.debian_pkg = kwargs.get('debian', [])
        if not self.debian_pkg:
            with open(join(CURRENT_DIR, 'deb.yaml')) as df:
                self.debian_pkg = yaml.load(df)
        # 需要安装的pip包
        self.pypi_pkg = kwargs.get('pypi', [])
        if not self.pypi_pkg:
            with open(join(CURRENT_DIR, 'pip.yaml')) as df:
                self.pypi_pkg = yaml.load(df)

        # apt源
        self.source_list = kwargs['apt'].get('sources', [])
        self.apt_use_proxy = kwargs['apt'].get('use_proxy', False)
        # pip源
        self.pip_index_url = kwargs['pip'].get('index')
        self.pip_trust_host = kwargs['pip'].get('trusted_host')
        self.pip_use_proxy = kwargs['pip'].get('use_proxy', False)
        # 访问公有云的路由器地址
        self.router = kwargs['router']
        # http_proxy
        self.http_proxy = kwargs.get('http_proxy')
        self.ssh_key = kwargs.get('ssh_key')

    def processCommand(self, context, args):
        """
            @Brief processCommand
            @Param context:
            @Param args:
                install_host: 要安装的机器, 使用配置文件中的resource_name, 默认是全部
                pkg_type: 需要安装的包类型,  pip | deb
                pkg_name: 需要安装的包名
        """
        # 生成主机列表
        host_list = []
        if not args.install_host:
            host_list = self.getHostList(context)
        else:
            for item in args.install_host:
                host_list.append(context.resources[item].ip)
        if not host_list:
            raise ValueError('no host to deploy')
        for item in args.pkg_name:
            execute(self.installPackage, args.pkg_type, item, hosts=host_list)

    def ip2host(self, ip):
        '''
            根据ip返回主机名
        '''
        for item in self.resources:
            if item.ip == ip:
                return item.hostname
        return None

    def authorizeSSH(self):
        '''
            @Brief: 添加ssh key， 允许无密码访问
        '''
        sudo("mkdir -p /root/.ssh/")
        append('/root/.ssh/authorized_keys', self.ssh_key, use_sudo=True)

    def addRouteTable(self, context):
        '''
            @Brief: 添加访问公有云的路由
        '''
        router_ip = context.resource(self.router).ip
        if not contains("/etc/network/interfaces", "route add -net 192.168.95.0/24"):
            with settings(warn_only=True):
                sudo('route add -net 192.168.95.0/24 gw %s' % router_ip)
            sed("/etc/network/interfaces",
                "^\(\s\+\)\(address\s\+%s\)" % env.host_string,
                "\1\2\\nup route add -net 192.168.95.0/24 gw %s" % router_ip, use_sudo=True)
        if not contains("/etc/network/interfaces", "route add -net 192.168.50.0/24"):
            with settings(warn_only=True):
                sudo('route add -net 192.168.50.0/24 gw %s' % router_ip)
            sed("/etc/network/interfaces",
                "^\(\s\+\)\(address\s\+%s\)" % env.host_string,
                "\1\2\\nup route add -net 192.168.50.0/24 gw %s" % router_ip, use_sudo=True)

    def addAptProxy(self):
        '''
            @Brief: 为apt-get配置代理
        '''
        sudo('''echo "Acquire::http::Proxy "%s";" > /etc/apt/apt.conf''' %
             self.http_proxy)

    def replaceAptSourceList(self):
        '''
            @Brief: 替换APT源
        '''
        append("/etc/apt/sources.list", self.source_list, use_sudo=True)

    def replacePipConf(self):
        '''
            @Brief: 配置/etc/pip.conf, 包括index-url, trusted-host, proxy

        '''
        if self.http_proxy and self.pip_use_proxy:
            proxy_string = "proxy = %s" % self.http_proxy
        else:
            proxy_string = ""
        pip_config_content = '''
[global]
{proxy_string}
index-url = {index_url}

[install]
trusted-host={trusted_host}
        '''.format(
            index_url=self.pip_index_url,
            trusted_host=self.pip_trust_host,
            proxy_string=proxy_string
        )
        put(local_path=StringIO.StringIO(pip_config_content),
            remote_path="/etc/pip.conf", use_sudo=True)

    def installPip(self):
        '''
            @Brief: 安装pip
        '''
        # 检查是否已经安装
        with settings(warn_only=True):
            result = sudo("pip --version")
            if not result.failed:
                return

        # 安装pip
        put(join(CURRENT_DIR, 'get-pip.py'), '/tmp/get-pip.py', use_sudo=True)
        if self.http_proxy and self.pip_use_proxy:
            proxy_cmd = "http_proxy=%s " % self.http_proxy
        else:
            proxy_cmd = ""
        sudo("{proxy_cmd}python /tmp/get-pip.py -q --disable-pip-version-check")

    def installCA(self):
        '''
            @Brief: 安装证书
        '''
        sudo('mkdir -p /usr/local/share/ca-certificates/bdmd')
        put(join(CURRENT_DIR, 'bdmd.crt'), '/usr/local/share/ca-certificates/bdmd', use_sudo=True)
        sudo('update-ca-certificates')

    def __deploy__(self, context, **kwargs):
        '''
        '''
        # 设置主机名
        execute(self.setHostName, hosts=self.getHostList(context))
        # 添加ssh key
        if self.ssh_key:
            execute(self.authorizeSSH, hosts=self.getHostList(context))
        # 设置路由表
        if self.router:
            router_ip = context.resource(self.router).ip
            tmp_hosts = [ip for ip in self.getHostList(
                context) if ip != router_ip]
            execute(self.addRouteTable, context, hosts=tmp_hosts)

        # 设置apt源
        # 设置apt代理
        if self.source_list:
            execute(self.replaceAptSourceList, hosts=self.getHostList(context))

        if self.apt_use_proxy and self.http_proxy:
            execute(self.addAptProxy, hosts=self.getHostList(context))

        # 配置pip
        execute(self.replacePipConf, hosts=self.getHostList(context))
        # 安装pip
        execute(self.installPip, hosts=self.getHostList(context))

        # 配置CA
        execute(self.installCA, hosts=self.getHostList(context))

        return True

    def setHostName(self):
        '''
            设置主机名
        '''
        hostname = self.ip2host(env.host_string)
        sudo("hostname  %s" % hostname)
        sudo('echo "%s" > /etc/hostname' % hostname)

    @retry(3)
    def installPackage(self, pkg_type, pkg_name):
        '''
            安装debian和pip包, 这里的安装允许出错
        '''
        with settings(warn_only=True):
            if pkg_type == 'deb':
                ret = sudo("apt-get install -y --force-yes -qq %s" % pkg_name)
                if ret.failed:
                    LOG.error('[%s] install failed' % pkg_name)
                    return False
                else:
                    LOG.info('[%s] install successfully' % pkg_name)
                    return True
            elif pkg_type == 'pip':
                ret = sudo(
                    'pip install -q --disable-pip-version-check %s' % pkg_name)
                if ret.failed:
                    LOG.error('[%s] install failed' % pkg_name)
                    return False
                else:
                    LOG.info('[%s] install successfully' % pkg_name)
                    return True
        return True
