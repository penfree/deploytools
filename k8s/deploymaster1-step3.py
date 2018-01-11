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


def installDashboard(config):
    # 上传配置文件
    put(local_path=join(FILE_DIR, 'kube-dashboard'), remote_path='/root/k8sinstall/', use_sudo=True)
    # 安装dashboard
    sudo('kubectl create -f /root/k8sinstall/kube-dashboard/')


def installHeapster(config):
    # 允许在master上部署pod
    with settings(warn_only=True):
        sudo('kubectl taint nodes --all node-role.kubernetes.io/master-')
    
    # 上传配置文件
    put(local_path=join(FILE_DIR, 'kube-heapster'), remote_path='/root/k8sinstall/', use_sudo=True)
    # 安装heapster
    sudo('kubectl create -f /root/k8sinstall/kube-heapster')
    # 重启docker, kubelet
    sudo('systemctl restart docker kubelet')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installDashboard, config=config, hosts=[config.Master1.ip])
    execute(installHeapster, config=config, hosts=[config.Master1.ip])

main()