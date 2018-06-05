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
from fabric.contrib.files import append, upload_template, sed, comment, exists, contains
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
    put(local_path=join(FILE_DIR, 'docker-ce.repo'), remote_path='/etc/yum.repos.d/docker-ce.repo', use_sudo=True)
    put(local_path=join(FILE_DIR, 'k8s.repo'), remote_path='/etc/yum.repos.d/kubernetes.repo', use_sudo=True)
    sudo("yum makecache fast")


    # 关闭防火墙
    '''
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
    '''
    
    # 关闭selinux
    sudo("sed -i -e 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config")
    sudo('yum install -y wget lrzsz vim zip telnet net-tools rsync libxslt-devel python-devel gcc glibc-devel libcap-devel python-pycurl nfs-utils')

    with settings(warn_only=True):
        ret = sudo('pip --version')
        if ret.failed:
            sudo('wget ftp://192.168.95.2/get-pip.py -O /tmp/get-pip.py')
            sudo('python /tmp/get-pip.py')

    with settings(warn_only=True):
        ret = sudo('systemctl status firewalld')
        if ret.failed:
            sudo('systemctl unmask firewalld')
            sudo('systemctl enable firewalld')
            sudo('systemctl start firewalld')

    # 在所有kubernetes节点上允许kube-proxy的forward
    sudo('firewall-cmd --permanent --direct --add-rule ipv4 filter INPUT 1 -i docker0 -j ACCEPT -m comment --comment "kube-proxy redirects"')
    sudo('firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 1 -o docker0 -j ACCEPT -m comment --comment "docker subnet"')
    sudo('firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 1 -i flannel.1 -j ACCEPT -m comment --comment "flannel subnet"')
    sudo('firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 1 -o flannel.1 -j ACCEPT -m comment --comment "flannel subnet"')
    sudo('firewall-cmd --zone=public --add-port=16443/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=6443/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=4001/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=2379-2380/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10250/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10251/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10252/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10255/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=30000-32767/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10250/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=10255/tcp --permanent')
    sudo('firewall-cmd --zone=public --add-port=30000-32767/tcp --permanent')
    sudo('firewall-cmd --reload')
    # 在所有kubernetes节点上，删除iptables的设置，解决kube-proxy无法启用nodePort。（注意：每次重启firewalld必须执行以下命令?）
    sudo('iptables -D INPUT -j REJECT --reject-with icmp-host-prohibited')


    # 安装docker, kubeadm, kubelet
    sudo('yum install -y --setopt=obsoletes=0 docker-ce-{version} docker-ce-selinux-{version}'.format(version=config.DockerVersion))
    sudo('pip install  docker-compose==%s' % config.DockerComposeVersion)
    sudo('yum install -y kubelet-%s' % config.K8sVersion)
    sudo('yum install -y kubeadm-%s' % config.K8sVersion)
    sudo('yum install -y kubectl-%s' % config.K8sVersion)
    sudo('systemctl enable docker && systemctl start docker')
    sudo('systemctl enable kubelet && systemctl start kubelet')
    
    # 设置iptables
    append('/etc/sysctl.d/k8s.conf', 'net.bridge.bridge-nf-call-iptables = 1', use_sudo=True)
    append('/etc/sysctl.d/k8s.conf', 'net.bridge.bridge-nf-call-ip6tables = 1', use_sudo=True)
    sudo('sysctl -p /etc/sysctl.d/k8s.conf')

    # 修改docker配置
    docker_svc_config = '/usr/lib/systemd/system/docker.service'
    if not exists(docker_svc_config):
        docker_svc_config = '/etc/systemd/system/docker.service'
    if not exists(docker_svc_config):
        raise ValueError('cannot find docker systemd unit file')
    
    cmd = 'ExecStartPost=/usr/sbin/iptables -P FORWARD ACCEPT'
    if not contains(docker_svc_config, cmd):
        sed(filename=docker_svc_config, before='ExecStart=(.*)$', after='ExecStart=\\1\\n%s' % cmd, use_sudo=True)

    # 设置kubelet使用cgroupfs，与dockerd保持一致，否则kubelet会启动报错
    sudo("sed -i -e 's/--cgroup-driver=systemd/--cgroup-driver=cgroupfs/g' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf")
    # 允许不关闭swap
    append('/etc/systemd/system/kubelet.service.d/10-kubeadm.conf', 'Environment="KUBELET_EXTRA_ARGS=--fail-swap-on=false"')
    sudo('systemctl daemon-reload && systemctl restart kubelet')
    
    if not exists(config.ImagePath, use_sudo=True):
        sudo("wget ftp://192.168.95.2/k8s/k8s-%s.tar.gz -O %s" % (config.K8sVersion, config.ImagePath))
    
    # disable swap
    #sudo('swapoff -a')
    #sudo("sed -i -e 's/^\(.*\)swap\(.*\)$/#\1swap\2/g' /etc/fstab")


    # 导入所有docker镜像
    sudo('docker load -i %s' % config.ImagePath)


def installKeepAlived(config):
    sudo('yum install -y keepalived')
    sudo('systemctl enable keepalived && systemctl restart keepalived')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    execute(basicConfig, config=config, hosts=config.getAllHosts())
    execute(installKeepAlived, config=config, hosts=config.getMasters())

if __name__ == '__main__':
    main()