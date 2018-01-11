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


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    return parser.parse_args()


def scalePods(config):
    sudo('kubectl scale --replicas=3 -n kube-system deployment/kube-dns')
    sudo('kubectl scale --replicas=3 -n kube-system deployment/kubernetes-dashboard')
    sudo('kubectl scale --replicas=3 -n kube-system deployment/heapster')
    sudo('kubectl scale --replicas=3 -n kube-system deployment/monitoring-grafana')
    sudo('kubectl scale --replicas=3 -n kube-system deployment/monitoring-influxdb')


def installKeepalived(config):
    sudo('yum install -y keepalived')

    # 备份配置文件
    # sudo('mv /etc/keepalived/keepalived.conf /etc/keepalived/keepalived.conf.bak')
    priority = 256 - int(env.host_string.split('.')[-1])
    if env.host_string == config.Master1.ip:
        state = 'MASTER'
    else:
        state = 'BACKUP'
    upload_template(
        join(FILE_DIR, 'keepalived.conf'),
        '/etc/keepalived/keepalived.conf',
        context={
            'masterIP1': config.Master1.ip,
            'virtualIP': config.VirtualIP,
            'priority': str(priority),
            'state': state,
            'interface': config.Interface
        },
        use_sudo=True
    )
    put(local_path=join(FILE_DIR, 'check_apiserver.sh'), remote_path='/etc/keepalived/check_apiserver.sh', use_sudo=True, mode=0755)
    sudo('systemctl restart keepalived')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(scalePods, config, hosts=[config.Master1.ip])

    execute(installKeepalived, config, hosts=config.getMasters())

main()