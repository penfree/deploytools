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

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DIR = os.path.join(CURRENT_DIR, 'files')
TMP_DIR = os.path.join(CURRENT_DIR, 'tmp')


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    return parser.parse_args()


def uploadConfig(config, local_dir):
    if exists('/etc/kubernetes'):
        sudo('rm -rf /etc/kubernetes')
        sudo('mkdir -p /etc/kubernetes/')
    put(
        local_path=join(local_dir, '*'),
        remote_path='/etc/kubernetes/',
        use_sudo=True
    )
    # 重新启动kubelet
    sudo('systemctl daemon-reload && systemctl restart docker kubelet')


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    # 修改master2, master3配置
    if os.path.exists(join(TMP_DIR, 'k8sconfig_master2')):
        local('rm -rf %s' % join(TMP_DIR, 'k8sconfig_master2'))
    if os.path.exists(join(TMP_DIR, 'k8sconfig_master3')):
        local('rm -rf %s' % join(TMP_DIR, 'k8sconfig_master3'))
    
    for dirpath, _, filenames in os.walk(join(TMP_DIR, 'k8sconfig_master1')):
        for filename in filenames:
            m1_path = join(dirpath, filename)
            m2_dirpath = dirpath.replace('k8sconfig_master1', 'k8sconfig_master2')
            if not os.path.exists(m2_dirpath):
                local('mkdir -p %s' % m2_dirpath)
            m3_dirpath = dirpath.replace('k8sconfig_master1', 'k8sconfig_master3')
            if not os.path.exists(m3_dirpath):
                local('mkdir -p %s' % m3_dirpath)
            m2_path = join(m2_dirpath, filename)
            m3_path = join(m3_dirpath, filename)

            with open(m1_path) as df:
                content = df.read()
            if filename == 'kube-apiserver.yaml':
                pat = re.compile(ur'--advertise-address=\d+\.\d+\.\d+\.\d+')             
                m2_content = pat.sub('--advertise-address=%s' % config.Master2.ip, content)
                m3_content = pat.sub('--advertise-address=%s' % config.Master3.ip, content)
            elif filename in ('kubelet.conf', 'admin.conf', 'controller-manager.conf', 'scheduler.conf'):
                pat = re.compile(ur'server:\s*https://\d+\.\d+\.\d+\.\d+:6443')
                m2_content = pat.sub('server: https://%s:6443' % config.Master2.ip, content)
                m3_content = pat.sub('server: https://%s:6443' % config.Master3.ip, content)
            else:
                m2_content = content
                m3_content = content
            with open(m2_path, 'w') as df:
                df.write(m2_content)
            with open(m3_path, 'w') as df:
                df.write(m3_content)
    
    # 上传修改后的配置
    execute(uploadConfig, config, join(TMP_DIR, 'k8sconfig_master2'), hosts=[config.Master2.ip])
    execute(uploadConfig, config, join(TMP_DIR, 'k8sconfig_master3'), hosts=[config.Master3.ip])
                
main()