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

import time
from modules.modulebase import ModuleBase
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DNSModule(ModuleBase):
    NAME = 'dns-server'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        if len(self.resources) != 1:
            raise ValueError(
                'dns-server must specify one and only one resource')
        self.dns_server = self.resources[0]
        self.options = kwargs['options']
        # 除服务器以外，需要添加的DNS解析记录
        self.records = kwargs.get('records', [])
        # 服务器所在网段
        self.subnet = kwargs['subnet']
        # 院内DNS
        self.inner_dns = kwargs.get('inner_dns', ['223.5.5.5', '223.6.6.6'])

        self.reverse_ip = '.'.join(self.subnet.split('.')[:3][::-1])

    def __deploy__(self, context, **kwargs):
        '''
            部署dns
        '''
        self.domain = context.domain
        # 安装bind9
        execute(self.install, hosts=[self.dns_server.ip])
        # 配置
        execute(self.genOptions, hosts=[self.dns_server.ip])
        execute(self.genZones, hosts=[self.dns_server.ip])
        execute(self.genDB, context, hosts=[self.dns_server.ip])
        # 重启
        execute(self.restart, hosts=[self.dns_server.ip])
        # 修改所有机器的resolve.conf
        all_host = [res.ip for res in context.resources.values()]
        execute(self.modifyResolvconf, context, hosts=all_host)
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
            result = sudo('service bind9 status')
        return not result.failed

    def install(self):
        '''
            安装dns
        '''
        with settings(warn_only=True):
            sudo('apt-get update -qq')
        sudo('apt-get install -qq -y --force-yes bind9')

    def modifyResolvconf(self, context):
        """修改所有机器的dns配置,这里只是临时修改,需要手动在interface中配置以永久生效"""

        sed('/etc/resolv.conf', before='^nameserver.*',
            after='nameserver %s' % self.dns_server.ip, use_sudo=True)
        sed('/etc/resolv.conf', before='^search.*', after='search %s' %
            context.domain, use_sudo=True)

    def restart(self):
        '''
            重启dns服务
        '''
        sudo('service bind9 restart')

    def genOptions(self):
        '''
            @Brief: 生成named.conf.options
        '''
        forwarders = ';'.join(self.inner_dns)
        upload_template(os.path.join(CURRENT_DIR, 'named.conf.options.template'), '/etc/bind/named.conf.options', context={
            'forwarders': forwarders, 'subnet': self.subnet
        })

    def genZones(self):
        '''
            添加zone
        '''
        main_zone = {
            'name': self.domain,
            'type': 'master',
            'file': '"/etc/bind/db.%s"' % self.domain
        }
        revert_zone = {
            'name': '%s.in-addr.arpa' % self.reverse_ip,
            'type': 'master',
            'file': '"/etc/bind/db.%s"' % self.reverse_ip
        }
        bdmd_zone = {
            'name': 'bdmd.com',
            'type': 'forward',
            'forwarders': "{192.168.50.2;}"
        }
        zones = []
        zones.append(bdmd_zone)
        zones.append(main_zone)
        zones.append(revert_zone)

        zone_file = StringIO.StringIO()
        with open(os.path.join(CURRENT_DIR, 'named.conf.default-zones')) as df:
            zone_file.write(df.read())

        for zone in zones:
            zone_file.write('zone "%s" {\n' % zone['name'])
            for k, v in zone.iteritems():
                if k == 'name':
                    continue
                zone_file.write('    %s %s;\n' % (k, v))
            zone_file.write('};\n')
        put(zone_file, '/etc/bind/named.conf.default-zones', use_sudo=True)

    def genDB(self, context):
        '''
            生成数据库文件
        '''
        records = []
        # 添加物理机器的dns记录
        for item in context.resources.values():
            short_name = item.hostname.split('.')[0]
            records.append('%s  IN  A   %s' % (short_name, item.ip))

        # 添加额外的dns记录
        for item in self.records:
            if isinstance(item, basestring):
                records.append(item)
            if not isinstance(item, dict) or not item.get('hostname') or not item.get('ip'):
                continue
            if not item['hostname'].endswith(self.domain):
                LOG.warn('dns record must endwith %s' % self.domain)
                continue
            short_name = item['hostname'].split('.')[0]
            records.append('%s  IN  A   %s' % (short_name, item['ip']))

        # 为etcd增加SRV记录
        etcd_module = context.module('etcd')
        if etcd_module is not None:
            records.extend(etcd_module.getDnsRecord(context))

        upload_template(os.path.join(CURRENT_DIR, 'db.template'), '/etc/bind/db.%s' % self.domain,
                        context={
                            'domain': self.domain, 'dns_server_ip': self.dns_server.ip, 'records': '\n'.join(records)},
                        use_sudo=True)

        revert_records = []
        for item in context.resources.values():
            short_ip = item.ip.split('.')[-1]
            revert_records.append('%s  IN  PTR   %s.' %
                                  (short_ip, item.hostname))
        upload_template(os.path.join(CURRENT_DIR, 'db.revert.template'), '/etc/bind/db.%s' % self.reverse_ip,
                        context={'domain': self.domain,
                                 'records': '\n'.join(revert_records)},
                        use_sudo=True)
