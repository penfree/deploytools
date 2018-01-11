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


def installEtcd(config):
    '''
        安装etcd
    '''
    if env.host_string == config.Master1.ip:
        name = 'etcd0'
    elif env.host_string == config.Master2.ip:
        name = 'etcd1'
    elif env.host_string == config.Master3.ip:
        name = 'etcd2'
    else:
        raise ValueError('unknow ip %s' % env.host_string)
    
    with settings(warn_only=True):
        sudo('docker stop etcd')
        sudo('docker rm etcd')
        sudo('rm -rf /var/lib/etcd-cluster/')
    
    sudo('''docker run -d --restart always -v /etc/ssl/certs:/etc/ssl/certs -v /var/lib/etcd-cluster:/var/lib/etcd -p 4001:4001 -p 2380:2380 -p 2379:2379 --name etcd gcr.io/google_containers/etcd-amd64:3.0.17 etcd --name={name} --advertise-client-urls=http://{ip}:2379,http://{ip}:4001 --listen-client-urls=http://0.0.0.0:2379,http://0.0.0.0:4001 --initial-advertise-peer-urls=http://{ip}:2380 --listen-peer-urls=http://0.0.0.0:2380 --initial-cluster-token=9477af68bbee1b9ae037d6fd9e7efefd --initial-cluster=etcd0=http://{master_ip1}:2380,etcd1=http://{master_ip2}:2380,etcd2=http://{master_ip3}:2380 --initial-cluster-state=new --auto-tls --peer-auto-tls --data-dir=/var/lib/etcd'''.format(
        ip=env.host_string,
        master_ip1=config.Master1.ip,
        master_ip2=config.Master2.ip,
        master_ip3=config.Master3.ip,
        name=name
    ))


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installEtcd, config=config, hosts=config.getMasters())


main()