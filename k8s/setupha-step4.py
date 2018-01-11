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


def installNginx(config):
    sudo('mkdir -p /root/k8sinstall/')
    with settings(warn_only=True):
        sudo('docker stop nginx-lb')
        sudo('docker rm nginx-lb')
    # 上传配置文件
    upload_template(
        filename=join(FILE_DIR, 'nginx-default.conf'),
        destination='/root/k8sinstall/nginx-default.conf',
        context={
            'masterIP1': config.Master1.ip,
            'masterIP2': config.Master2.ip,
            'masterIP3': config.Master3.ip,
            'haPort': config.ApiHAPort
        },
        use_sudo=True
    )
    sudo('docker run -d -p %s:%s --name nginx-lb --restart always -v /root/k8sinstall/nginx-default.conf:/etc/nginx/nginx.conf nginx' % (config.ApiHAPort, config.ApiHAPort))


def updateProxy(config):
    sudo('''kubectl get -n kube-system configmap/kube-proxy -o json | sed 's^server: https://{masterIP1}:6443^server: https://{virtualIP}:{apiHAPort}^' | kubectl replace -f -'''.format(
        masterIP1=config.Master1.ip,
        virtualIP=config.VirtualIP,
        apiHAPort=config.ApiHAPort
    ))


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installNginx, config, hosts=config.getMasters())
    execute(updateProxy, config, hosts=[config.Master1.ip])

main()