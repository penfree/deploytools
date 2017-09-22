#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 08:31:38 AM CST

# File Name: module.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging


class ModuleBase(object):
    '''
        定义一个私有云组件
    '''
    NAME = 'modulebase'

    def __init__(self, resource_map={}, group_map={}, **kwargs):
        # module将要部署的资源列表
        self.resources = []
        # 是否允许部署部分机器
        self.allow_partial_deploy = kwargs.get('allow_partial_deploy', False)

        # 初始化待部署机器列表
        resource_name_set = set()
        for group in kwargs.get('resgroups', []):
            if group not in group_map:
                raise ValueError('group[%s] is not defined' % group)
            else:
                for res in group_map[group].resources:
                    resource_name_set.add(res.name)

        for res in kwargs.get('resources', []):
            if res not in resource_map:
                raise ValueError('resource[%s] is not defined' % res)
            else:
                resource_name_set.add(res)
        for res in resource_name_set:
            self.resources.append(resource_map[res])

        # 不配置resource和resgroup的时候默认所有机器都部署
        if not self.resources:
            for res in resource_map.values():
                self.resources.append(res)

        # 优先级,默认都是1000,数字越小优先级越高
        self.priority = kwargs.get('priority', 1000)
        # 依赖的模块,不可以依赖比自己优先级高的模块
        self.require = kwargs.get('require', [])

        # 是否已经部署完成
        self.deployed = False
        # 模块是否只能手动执行
        self.manual_only = kwargs.get('manual_only', False)

    def getHostList(self, context):
        '''
            获取ip列表
        '''
        if self.allow_partial_deploy:
            return [res.ip for res in self.resources if not context.deploy_host or res.name in context.deploy_host]
        else:
            return [res.ip for res in self.resources]

    def check(self, context):
        '''
            检查安装是否完成
        '''
        return False

    def deploy(self, context, **kwargs):
        '''
            部署模块
        '''
        if not self.allow_partial_deploy and context.deploy_host:
            logging.error(
                'module[%s] does not allow partital deploy' % self.NAME)
            return False
        if not context.redeploy and self.check(context):
            logging.info("%s already deployed" % self.NAME)
            return True
        return self.__deploy__(context, **kwargs)

    def processCommand(self, context, args):
        """
            @Brief processCommand 处理针对该模块的命令
            @Param context:
            @Param args: 主程序接收到的命令行参数
        """
        raise NotImplementedError()
