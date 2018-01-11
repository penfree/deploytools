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


def basicConfig(config):
    # 配置repo
    put(local_path=join(FILE_DIR, 'k8s.repo'), remote_path='/etc/yum.repos.d/kubernetes.repo', use_sudo=True)
    sudo("yum makecache fast")

    # 关闭防火墙
    with settings(warn_only=True):
        ret = sudo('systemctl status firewalld')
        if not ret.failed:
            sudo('systemctl disable firewalld')
            sudo('systemctl stop firewalld')
            sudo('systemctl mask firewalld')
        ret = sudo('systemctl status iptables')
        if not ret.failed:
            sudo('systemctl disable iptables')
            sudo('systemctl stop iptables')
    
    # 关闭selinux
    sudo("sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config")

    # 设置iptables
    append('/etc/sysctl.d/k8s.conf', 'net.bridge.bridge-nf-call-iptables = 1', use_sudo=True)
    append('/etc/sysctl.d/k8s.conf', 'net.bridge.bridge-nf-call-ip6tables = 1', use_sudo=True)

    # 安装docker, kubeadm, kubelet
    sudo('yum install -y docker-%s' % config.DockerVersion)
    sudo('yum install -y kubelet-%s' % config.K8sVersion)
    sudo('yum install -y kubeadm-%s' % config.K8sVersion)
    sudo('yum install -y kubernetes-cni-0.5.1')
    sudo('systemctl enable docker && systemctl start docker')
    sudo('systemctl enable kubelet && systemctl start kubelet')

    # 导入所有docker镜像
    sudo('docker load -i %s' % config.ImagePath)


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(basicConfig, config=config, hosts=config.getAllHosts())


main()