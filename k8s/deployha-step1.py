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
    put, require, roles, run, runs_once, settings, show, sudo, warn, execute, get
from fabric.contrib.files import append, upload_template, sed, comment, exists
import os
from os.path import join
import logging

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DIR = os.path.join(CURRENT_DIR, 'files')
TMP_DIR = os.path.join(CURRENT_DIR, 'tmp')


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file')
    return parser.parse_args()


def installDashboard(config):
    sudo('kubectl taint nodes --all node-role.kubernetes.io/master-')
    with cd('/root/kubeadm-ha/'):
        sudo('kubectl apply -f kube-dashboard/')
        sudo('kubectl apply -f kube-heapster/influxdb/')
        sudo('kubectl apply -f kube-heapster/rbac/')


def downloadConfig(config):
    get(remote_path='/etc/kubernetes/pki/*', local_path=join(TMP_DIR, 'k8sconfig_master1', '%(path)s'))


def installStandbyMaster(config):
    sudo('kubeadm reset')

    if exists('/etc/kubernetes/pki'):
        sudo('rm -rf /etc/kubernetes/pki')
    sudo('mkdir -p /etc/kubernetes/pki')
    put(local_path=join(TMP_DIR, 'k8sconfig_master1', '*'), remote_path='/etc/kubernetes/pki/', use_sudo=True, mirror_local_mode=True)

    with cd('/root/kubeadm-ha/'):
        ret = sudo('kubeadm init --config=kubeadm-init.yaml --ignore-preflight-errors=Swap')
    
    with settings(warn_only=True):
        sudo('kubectl taint nodes --all node-role.kubernetes.io/master-')
    sudo('kubectl scale --replicas=2 -n kube-system deployment/kube-dns')


def installNginx(config):
    sudo('systemctl restart keepalived')
    with cd('/root/kubeadm-ha/'):
        sudo('docker-compose -f nginx-lb/docker-compose.yaml up -d')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    # 从master1上下载配置到 files/k8sconfig_master1
    if os.path.exists(join(TMP_DIR, 'k8sconfig_master1')):
        local('rm -rf %s' % join(TMP_DIR, 'k8sconfig_master1'))
        local('mkdir -p %s' % join(TMP_DIR, 'k8sconfig_master1'))
    execute(downloadConfig, config=config, hosts=[config.Master1.ip])

    # 上传配置到master2, master3, 并初始化master1, master2
    execute(installStandbyMaster, config, hosts=[config.Master2.ip, config.Master3.ip])

    # nginx负载均衡配置
    execute(installNginx, config, hosts=config.getMasters())


main()
