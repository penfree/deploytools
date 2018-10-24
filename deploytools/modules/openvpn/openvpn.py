#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


import logging
LOG = logging.getLogger("openvpn")
import os
import StringIO

import time
from modules.modulebase import ModuleBase
from os.path import join
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
from collections import namedtuple

VpnConfig = namedtuple('VpnConfig', 'cert,key,name')


class OpenvpnModule(ModuleBase):
    NAME = 'openvpn'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        ModuleBase.__init__(self, resource_map, group_map, **kwargs)
        if not kwargs.get('clients'):
            raise ValueError('At least 1 server is need to install openvpn client')
        self.clients = []
        for item in kwargs.get('clients', []):
            self.clients.append(VpnConfig(cert=item['cert'], key=item['key'], name=item['name']))
        # VPN Server地址:
        #   如果服务器能访问公网，则直接使用tun.iyoudoctor.com
        #   如果使用跳板机，则在跳板机上通过创建端口映射，这里填写映射后的ip和端口
        self.server_ip = kwargs.get('server_ip', 'tun.iyoudoctor.com')
        self.server_port = kwargs.get('server_port', 10190)

    def installStunnel(self, context):
        '''
            @Brief: 安装stunnel
        '''
        put(
            local_path=join(CURRENT_DIR, 'stunnel-4.56-6.el7.x86_64.rpm'),
            remote_path='/tmp/stunnel.rpm',
            use_sudo=True
        )
        with settings(warn_only=True):
        #    sudo('systemctl stop firewalld')
        #    sudo('systemctl mask firewalld')
            sudo('setenforce 0')
        put(
            local_path=join(CURRENT_DIR, 'pkcs11-helper-1.11-3.el7.x86_64.rpm'),
            remote_path='/tmp/pkcs11-helper.rpm',
            use_sudo=True
        )
        with settings(warn_only=True):
            ret = sudo('rpm -i /tmp/pkcs11-helper.rpm')
            if ret.failed and 'already installed' not in ret.stdout and 'already installed' not in ret.stderr:
                raise ValueError('Install pkcs11-helper failed')

        with settings(warn_only=True):
            ret = sudo('rpm -i /tmp/stunnel.rpm')
            if ret.failed and 'already installed' not in ret.stdout and  'already installed' not in ret.stderr:
                raise ValueError('Install stunnel failed')


        # 修改stunnel配置
        put(
            local_path=join(CURRENT_DIR, 'stunnel-server.pem'),
            remote_path='/etc/stunnel/server.pem',
            use_sudo=True
        )
        upload_template(
            filename=join(CURRENT_DIR, 'stunnel.conf'),
            destination='/etc/stunnel/stunnel.conf',
            context={
                'serverIP': self.server_ip,
                'serverPort': self.server_port
            },
            use_sudo=True
        )
        put(
            local_path=join(CURRENT_DIR, 'tun.iyoudoctor.com.cert.pem'),
            remote_path='/etc/stunnel/tun.iyoudoctor.com.cert.pem',
            use_sudo=True
        )
        put(
            local_path=join(CURRENT_DIR, 'tun.iyoudoctor.com.key.pem'),
            remote_path='/etc/stunnel/tun.iyoudoctor.com.key.pem',
            use_sudo=True
        )
        put(
            local_path=join(CURRENT_DIR, 'stunnel.service'),
            remote_path='/lib/systemd/system/stunnel.service',
            use_sudo=True
        )
        sudo('systemctl enable stunnel.service')
        sudo('systemctl restart stunnel.service')

    def installOpenvpn(self, context):
        '''
            @Brief: 安装openvpn
        '''
        with settings(warn_only=True):
        #    sudo('systemctl stop firewalld')
        #    sudo('systemctl mask firewalld')
            sudo('setenforce 0')

        put(
            local_path=join(CURRENT_DIR, 'openvpn-2.4.3-1.el7.x86_64.rpm'),
            remote_path='/tmp/openvpn.rpm',
            use_sudo=True
        )
        with settings(warn_only=True):
            ret = sudo('rpm -i /tmp/openvpn.rpm')
            if ret.failed and 'already installed' not in ret.stdout and 'already installed' not in ret.stderr:
                raise ValueError('Install openvpn failed')

        # 配置openvpn
        put(join(CURRENT_DIR, 'ta.key'), '/etc/openvpn/', use_sudo=True)
        put(join(CURRENT_DIR, 'update-resolv-conf'), '/etc/openvpn/', use_sudo=True, mode='0755')
        put(join(CURRENT_DIR, 'setup_client_router.sh'), '/etc/openvpn/', use_sudo=True, mode='0755')
        put(join(CURRENT_DIR, 'vpn.cert.pem'), '/etc/openvpn/', use_sudo=True)
        tmp = env.host_string.split('.')
        tmp[-1] = '0'
        subnet = '.'.join(tmp)
        # put(join(CURRENT_DIR, 'up.sh'), '/etc/openvpn/', use_sudo=True, mode='0755')
        upload_template(
            join(CURRENT_DIR, 'up.sh'),
            '/etc/openvpn/up.sh',
            context={"subnet": subnet},
            use_sudo=True,
            mode='0755'
        )
        client = self.getClient(context, env.host_string)
        put(client.cert, '/etc/openvpn/', use_sudo=True)
        put(client.key, '/etc/openvpn/', use_sudo=True)
        upload_template(
            join(CURRENT_DIR, 'client.conf'),
            '/etc/openvpn/client.conf',
            context={'vpnCert': os.path.basename(client.cert), 'vpnKey': os.path.basename(client.key)}
        )
        sudo('systemctl enable openvpn@client.service')
        sudo('systemctl start openvpn@client.service')

    def getClient(self, context, ip):
        for item in self.clients:
            if context.resource(item.name).ip == ip:
                return item
        return None

    def __deploy__(self, context, **kwargs):
        '''
            部署openvpn
        '''
        all_client_ip = [
            context.resource(item.name).ip for item in self.clients
        ]
        print all_client_ip
        execute(self.installStunnel, context, hosts=all_client_ip)
        execute(self.installOpenvpn, context, hosts=all_client_ip)

        return True
