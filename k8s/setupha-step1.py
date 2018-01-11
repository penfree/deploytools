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
TMP_DIR = os.path.join(CURRENT_DIR, 'tmp')


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    return parser.parse_args()


def downloadConfig(config):
    get(remote_path='/etc/kubernetes/*', local_path=join(TMP_DIR, 'k8sconfig_master1', '%(path)s'))


def uploadConfig(config):
    if exists('/etc/kubernetes'):
        sudo('rm -rf /etc/kubernetes')
        sudo('mkdir -p /etc/kubernetes')
    put(local_path=join(TMP_DIR, 'k8sconfig_master1', '*'), remote_path='/etc/kubernetes/', use_sudo=True, mirror_local_mode=True)

    # 重启kubelet
    sudo('systemctl daemon-reload && systemctl restart kubelet')

    # 配置KUBECONFIG
    append('/root/.bashrc', 'export KUBECONFIG=/etc/kubernetes/admin.conf')
    sudo('source ~/.bashrc')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    # 从master1上下载配置到 files/k8sconfig_master1
    if os.path.exists(join(TMP_DIR, 'k8sconfig_master1')):
        local('rm -rf %s' % join(TMP_DIR, 'k8sconfig_master1'))
        local('mkdir -p %s' % join(TMP_DIR, 'k8sconfig_master1'))
    execute(downloadConfig, config=config, hosts=[config.Master1.ip])

    # 上传配置到master2, master3
    execute(uploadConfig, config, hosts=[config.Master2.ip, config.Master3.ip])

main()