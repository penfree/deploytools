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
    parser.add_argument('--config', dest='config_file')
    return parser.parse_args()


def resetAllMaster(config):
    '''
        @Brief: 初始化master1
    '''
    # 在所有master节点上重置网络
    sudo('systemctl stop kubelet')
    sudo('systemctl stop docker')
    sudo('rm -rf /var/lib/cni/ /var/lib/kubelet/* /etc/cni/')
    with settings(warn_only=True):
        sudo('ip link del docker0')
        sudo('ip link del flannel.1')
        sudo('ip link del cni0')
    sudo('systemctl restart docker && systemctl restart kubelet')
    # 在所有master节点上设置kubectl客户端连接
    append('/root/.bashrc',
           'export KUBECONFIG=/etc/kubernetes/admin.conf', use_sudo=True)
    # sudo('source /root/.bashrc')
    sudo('kubeadm reset')


def installMaster1(config):
    with cd('/root/kubeadm-ha/'):
        ret = sudo('kubeadm init --config=kubeadm-init.yaml --ignore-preflight-errors=Swap')
        # 记住输出的kubeadm join --token XXX --discovery-token-ca-cert-hash 
        print ret.stdout
        print ret.stderr
        sudo('kubectl apply -f kube-canal/')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(resetAllMaster, config=config, hosts=config.getMasters())
    execute(installMaster1, config=config, hosts=[config.Master1.ip])


main()
