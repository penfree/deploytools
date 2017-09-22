#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 08:04:49 AM CST

# File Name: install.py
# Description: 私有云部署脚本

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging
from argparse import ArgumentParser
import string
import datetime
import time
import os
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKING_DIR)
import subprocess
logging.basicConfig(level=logging.INFO)

LOG = logging.getLogger("oneclick")


def getArguments():
    '''
        Get Arugments
    '''
    parser = ArgumentParser("python oneclick/")
    subparsers = parser.add_subparsers(
        help='sub-command help', dest='submodule')

    parser.add_argument("--config", dest='config_file',
                        help='The Cloud Specific File', required=True)
    parser.add_argument("--silent", dest='silent', action='store_true',
                        default=False, help='Silent install, set all option to yes')
    parser.add_argument("--verbose", '-v', dest='verbose',
                        action='store_true', default=False, help='show more logs')
    parser.add_argument("--serial", dest='serial',
                        action='store_false', help='fabric run serial')
    parser.add_argument("--identity-file", '-i',
                        dest='identity_file', help="the ssh key file")
    parser.add_argument("--user", '-u', dest="user",
                        help="user name for deploy, must has sudo")
    parser.add_argument('--redeploy', dest='redeploy', action='store_true',
                        help='redeploy when module is already deployed')
    parser.add_argument('--deploy-host', dest='deploy_host',
                        help='only deploy on specified hosts', nargs='*')
    parser.add_argument('--gateway', dest='gateway')

    main_parser = subparsers.add_parser(
        'deploy', help='the main deploy parser')
    main_parser.add_argument(
        "--module", '-m', dest="module", help="Deploy only one module", nargs='*')
    main_parser.add_argument("--skip-failed-module", action='store_true', default=False,
                             dest="skip_failed_module", help="skip when module deployment failed")

    # 单独安装指定的包
    basic_parser = subparsers.add_parser('basic', help='install packages')
    basic_parser.add_argument('--install-host', dest='install_host',
                              help='which host [resource name in config file] to install the specified package, default to resources in config file', nargs='*')
    basic_parser.add_argument(
        '--pkg-type', dest='pkg_type', choices=['pip', 'deb'], help='pkg_type')
    basic_parser.add_argument(
        '--pkg-name', dest='pkg_name', help='package name', nargs='*')

    return parser.parse_args()


def do_work():
    from fabric.api import run
    result = run('hostname -f')
    print type(result), result.stdout


def main():
    args = getArguments()
    from util import ensureRequirements
    ensureRequirements()

    # 解析配置文件
    from common import Context
    from fabric.api import prompt, env
    from fabric.state import output as output_level
    if not args.verbose:
        output_level['status'] = False
        output_level['stdout'] = False

    context = Context(args.config_file, silent=args.silent,
                      redeploy=args.redeploy, deploy_host=args.deploy_host)
    if args.user:
        env.user = args.user
    else:
        env.user = prompt("Enter user name:", default="root")
    if args.identity_file:
        env.key_filename = args.identity_file
    else:
        env.password = prompt("Enter password:")
    if args.gateway:
        env.gateway = args.gateway
    env.parallel = args.serial

    # 如果是执行子模块命令
    if args.submodule != 'deploy':
        module = context.module(args.submodule)
        module.processCommand(context, args)
        exit(0)

    # 指定部署模块时,只部署该模块,若该模块依赖的模块未部署则退出
    white_list = set()
    if args.module:
        for module_name in args.module:
            module = context.module(module_name)
            for dep in module.require:
                m = context.module(dep)
                if not m or not m.check(context):
                    LOG.error('depend module[%s] of [%s] has not been deployed' % (
                        dep, module_name))
                    exit(0)
            white_list.add(module_name)

    # 遍历直到所有模块都已部署完
    finished = False
    module_list = sorted([(module_name, module) for module_name,
                          module in context.modules.iteritems()], key=lambda a: a[1].priority)
    while not finished:
        finished = True
        all_not_ready = True
        for module_name, module in module_list:
            if module.deployed:
                continue
            # 该模块只能手动部署
            if not white_list and module.manual_only:
                continue
            if white_list and module_name not in white_list:
                continue
            if context.moduleReady(module_name):
                all_not_ready = False
                LOG.info("deploy %s" % module_name)
                try:
                    res = module.deploy(context)
                except Exception, e:
                    LOG.exception(e)
                    res = False
                module.deployed = res
                if not res:
                    LOG.error("%s deploy failed" % module_name)
                    if not args.skip_failed_module:
                        exit(1)
                else:
                    module.deployed = True
            else:
                LOG.info("%s is not ready to deploy" % module_name)
                finished = False
        if all_not_ready:
            break

exit(main())
