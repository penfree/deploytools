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


def installFlannel(config):
    '''
        @Brief: 安装flannel
    '''
    # 安装flannel
    sudo('mkdir -p /root/k8sinstall/kube-flannel')
    # 上传配置文件
    upload_template(
        filename=join(FILE_DIR, 'kube-flannel', 'step2-kube-flannel-v0.7.1.yml'),
        destination='/root/k8sinstall/kube-flannel/step2-kube-flannel-v0.7.1.yml',
        context={
            'podSubnet': config.PodSubnet
        },
        use_sudo=True
    )
    put(
        local_path=join(FILE_DIR, 'kube-flannel', 'step1-kube-flannel-rbac-v0.7.1.yml'),
        remote_path='/root/k8sinstall/kube-flannel/step1-kube-flannel-rbac-v0.7.1.yml',
        use_sudo=True
    )
    sudo('kubectl create -f /root/k8sinstall/kube-flannel')
    

def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installFlannel, config=config, hosts=[config.Master1.ip])

main()