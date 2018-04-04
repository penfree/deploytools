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


def installDashboard(config):
    sudo('kubectl taint nodes --all node-role.kubernetes.io/master-')
    with cd('/root/kubeadm-ha/'):
        sudo('kubectl apply -f kube-dashboard/')
        sudo('kubectl apply -f kube-heapster/influxdb/')
        sudo('kubectl apply -f kube-heapster/rbac/')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installDashboard, config=config, hosts=[config.Master1.ip])


main()
