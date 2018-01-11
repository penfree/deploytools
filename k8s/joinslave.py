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


def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-q', dest='quiet', action='store_true')
    parser.add_argument('--config', dest='config_file', required=True)
    parser.add_argument('--slave', dest='slave', help='要加入的slave ip')
    return parser.parse_args()


def getToken(config):
    ret = sudo('kubeadm token list')
    for line in ret.stdout.split('\n'):
        words = re.split('\s+', line)
        if words[0] == 'TOKEN':
            continue
        else:
            return words[0]
    return None


def joinCluster(config, token):
    sudo('kubeadm join --token %s %s:%s' % (token, config.VirtualIP, config.ApiHAPort))


def main():
    args = getArgument()
    config = InstallConfig.loadConfig(args.config_file)
    config.initFabric(not args.quiet)

    # 从master1上获取token
    result = execute(getToken, config, hosts=[config.Master1.ip])
    token = result.get(config.Master1.ip)
    if not token:
        raise ValueError('Cannot get Token')
    else:
        print 'Token: %s' % token
    
    if args.slave:
        execute(joinCluster, config, token, hosts=[args.slave])
    else:
        execute(joinCluster, config, token, hosts=config.Slaves)

main()