#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from installconfig import InstallConfig
from argparse import ArgumentParser
from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute
from fabric.contrib.files import append, upload_template, sed, comment, exists
import os
from os.path import join
import logging

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DIR = os.path.join(CURRENT_DIR, 'files')
TOP_DIR = os.path.dirname(CURRENT_DIR)


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    return parser.parse_args()


def prepareConfig(config):
    """准备配置文件
    """
    put(local_path=join(FILE_DIR, 'kubeadm-ha'), remote_path='/root/', use_sudo=True)

    if env.host_string == config.Master1.ip:
        name = 'etcd1'
        priority = 102
    elif env.host_string == config.Master2.ip:
        name = 'etcd2'
        priority = 101
    elif env.host_string == config.Master3.ip:
        name = 'etcd3'
        priority = 100
    else:
        raise ValueError('unknow ip %s' % env.host_string)
    # 上传配置文件
    upload_template(
        filename=join(FILE_DIR, 'kubeadm-ha', 'create-config.sh'),
        destination='/root/kubeadm-ha/create-config.sh',
        context={
            'masterName1': config.Master1.hostname,
            'masterName2': config.Master2.hostname,
            'masterName3': config.Master3.hostname,
            'masterIP1': config.Master1.ip,
            'masterIP2': config.Master2.ip,
            'masterIP3': config.Master3.ip,
            'virtualIP': config.VirtualIP,
            'podSubnet': config.PodSubnet.replace('/', '\\\\/'),
            'svcSubnet': config.SvcSubnet.replace('/', '\\\\/'),
            'localIP': env.host_string,
            'kaState': 'MASTER' if env.host_string == config.Master1.ip else 'BACKUP',
            'etcdName': name,
            'priority': priority,
            'interface': config.Interface,
            'gateway': config.NetworkGateway,
        },
        use_sudo=True
    )
    with cd('/root/kubeadm-ha'):
        sudo('bash ./create-config.sh')


def installEtcd(config):
    '''
        安装etcd
    '''
    sudo('kubeadm reset')
    sudo('rm -rf /var/lib/etcd-cluster')
    with cd('/root/kubeadm-ha/'):
        sudo('docker-compose --file etcd/docker-compose.yaml stop')
        sudo('docker-compose --file etcd/docker-compose.yaml rm -f')
        sudo('docker-compose --file etcd/docker-compose.yaml up -d')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(prepareConfig, config=config, hosts=config.getMasters())
    execute(installEtcd, config=config, hosts=config.getMasters())


main()