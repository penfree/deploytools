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
import re
from preinstall import basicConfig
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DIR = os.path.join(CURRENT_DIR, 'files')


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    parser.add_argument('--slave', dest='slave', help='要加入的slave ip')
    parser.add_argument('--init', dest='init', help='是否需要初始化', action='store_true', default=False)

    return parser.parse_args()


def joinCluster(config):
    sudo('kubeadm reset')
    sudo('kubeadm join --ignore-preflight-errors=Swap --token %s %s:%s --discovery-token-ca-cert-hash %s' % (config.Token, config.Master1.ip, 6443, config.TokenHash))

    # 将slave节点上server修改为高可用的虚拟IP和负载均衡的16443端
    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/bootstrap-kubelet.conf'.format(master=config.Master1.ip, vip=config.VirtualIP))
    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/bootstrap-kubelet.conf'.format(master=config.Master2.ip, vip=config.VirtualIP))
    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/bootstrap-kubelet.conf'.format(master=config.Master3.ip, vip=config.VirtualIP))

    time.sleep(5)

    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/kubelet.conf'.format(master=config.Master1.ip, vip=config.VirtualIP))
    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/kubelet.conf'.format(master=config.Master2.ip, vip=config.VirtualIP))
    sudo('sed -i "s/{master}:6443/{vip}:16443/g" /etc/kubernetes/kubelet.conf'.format(master=config.Master3.ip, vip=config.VirtualIP))
    sudo('systemctl restart docker kubelet')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)
    
    if args.slave:
        if args.init:
            execute(basicConfig, config, hosts=[args.slave])
        execute(joinCluster, config, hosts=[args.slave])
    else:
        if args.init:
            execute(basicConfig, config, hosts=config.Slaves)
        execute(joinCluster, config, hosts=config.Slaves)

main()
