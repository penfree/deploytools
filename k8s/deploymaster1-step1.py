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


def installMaster(config):
    '''
        @Brief: 初始化master1
    '''
    sudo('mkdir -p /root/k8sinstall/')
    # 上传配置文件
    upload_template(
        filename=join(FILE_DIR, 'kubeadm-init-v1.7.x.yaml'),
        destination='/root/k8sinstall/kubeadm-init.yaml',
        context={
            'masterName1': config.Master1.hostname,
            'masterName2': config.Master2.hostname,
            'masterName3': config.Master3.hostname,
            'masterIP1': config.Master1.ip,
            'masterIP2': config.Master2.ip,
            'masterIP3': config.Master3.ip,
            'virtualIP': config.VirtualIP,
            'podSubnet': config.PodSubnet,
            'k8sVersion': config.K8sVersion,
            'apiDNSName': config.ApiDNSName
        },
        use_sudo=True
    )
    # 在k8s-master1上使用kubeadm初始化kubernetes集群，连接外部etcd集群
    sudo('kubeadm init --config=/root/k8sinstall/kubeadm-init.yaml')
    # 在k8s-master1上修改kube-apiserver.yaml的admission-control，v1.7.0使用了NodeRestriction等安全检查控制，务必设置成v1.6.x推荐的admission-control配置
    sed(
        '/etc/kubernetes/manifests/kube-apiserver.yaml',
        before='--admission-control=.*$',
        after='--admission-control=NamespaceLifecycle,LimitRanger,ServiceAccount,PersistentVolumeLabel,DefaultStorageClass,ResourceQuota,DefaultTolerationSeconds',
        use_sudo=True,
        backup=''
    )
    # 在k8s-master1上重启docker kubelet服务
    sudo('systemctl restart docker kubelet')
    # 在k8s-master1上设置kubectl的环境变量KUBECONFIG，连接kubelet
    append('/root/.bashrc',
           'export KUBECONFIG=/etc/kubernetes/admin.conf', use_sudo=True)
    # sudo('source /root/.bashrc')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(installMaster, config=config, hosts=[config.Master1.ip])


main()
