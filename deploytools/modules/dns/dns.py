#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 10:08:00 PM CST

# File Name: modules/dns.py
# Description: Deploy DNS Server

Steps:
    1. 修改name.conf.default-zones: 增加当前域, 反向DNS域和bdmd.com域
    2. 修改name.conf.options: 
        1) 增加forwarder,配置为医院的dns服务. 
        2) 配置allow-query, 仅允许本地访问DNS
    3. 配置dns记录的数据库文件,并加入其他需要解析的域名.
    4. 配置反向dns记录的数据库文件

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import logging
LOG = logging.getLogger("dns-server")
import os
import StringIO

from os.path import join
import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DNSModule(ModuleBase):
    NAME = 'dns'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        if len(self.resources) != 1:
            raise ValueError(
                'dns-server must specify one and only one resource')
        self.dns_server = self.resources[0]
        # 除服务器以外，需要添加的DNS解析记录
        self.records = kwargs.get('records', [])
        # 服务器所在网段
        self.subnet = kwargs['subnet']

        self.reverse_ip = '.'.join(self.subnet.split('.')[:3][::-1])

    def __deploy__(self, context, **kwargs):
        '''
            部署dns
        '''
        self.domain = context.domain
        # 安装bind9
        execute(self.install, context, hosts=[self.dns_server.ip])
        return True

    def check(self, context):
        """
            @Brief 检查dns-server是否已经部署完成
            @Param context:
        """
        result = execute(self.checkDNS, hosts=[self.dns_server.ip])
        if result.get(self.dns_server.ip):
            return True
        return False

    def checkDNS(self):
        """checkDNS"""
        with settings(warn_only=True):
            result = sudo('systemctl status named')
        return not result.failed

    def install(self, context):
        '''
            安装dns
        '''
        sudo('yum install -y bind bind-utils')
        # 配置named.conf
        upload_template(
            join(CURRENT_DIR, 'named.conf'), 
            '/etc/named.conf',
            context={
                'serverIP': self.dns_server.ip,
                'subnet': self.subnet,
                'reverseIP': self.reverse_ip,
                'domain': context.domain,
                'publicServer': '192.168.50.2'
            },
            use_sudo=True
        )
        # 配置正向解析记录
        records = []
        for _, res in context.resources.iteritems():
            if res.hostname.endswith(context.domain):
                name = res.hostname[:-len(context.domain) - 1]
            else:
                name = res.hostname
            records.append('{name}      IN  A           {ip}'.format(
                ip=res.ip,
                name=name
            ))
        for item in self.records:
            if item['hostname'].endswith(context.domain):
                name = item['hostname'][:-len(context.domain) - 1]
            else:
                name = item['hostname']
            records.append('{name}      IN  A           {ip}'.format(
                ip=res.ip,
                name=name
            ))
        
        upload_template(
            join(CURRENT_DIR, 'named.template'),
            '/var/named/named.%s' % context.domain,
            context={
                'serverIP': self.dns_server.ip,
                'domain': context.domain,
                'records': '\n'.join(records)
            },
            use_sudo=True
        )
    
        # 配置反向dns
        records = []
        for _, res in context.resources.iteritems():
            records.append('{ip}      IN  PTR           {name}.'.format(
                ip=res.ip.split('.')[-1],
                name=res.hostname
            ))

        upload_template(
            join(CURRENT_DIR, 'named.reverse.template'),
            '/var/named/named.reverse.%s' % context.domain,
            context={
                'domain': context.domain,
                'records': '\n'.join(records)
            }
        )
        sudo('systemctl restart named')
        sudo('firewall-cmd --add-service=dns --permanent')
        sudo('firewall-cmd --reload')
