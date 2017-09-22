#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Sat 16 Jan 2016 08:22:14 AM CST

# File Name: common/contextmanager.py
# Description: 私有云配置

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import yaml
from resource import Resource
from resgroup import ResourceGroup
from modules import NAME2MODULE
import logging
LOG = logging.getLogger("context")


class Context(object):

    def __init__(self, file_path, offline=False, **kwargs):
        # 机器列表
        self._resources = {}
        # 机器分组列表
        self._resgroups = {}
        # 模块列表
        self._modules = {}
        # 离线安装
        self.offline = offline
        # 静默安装
        self.silent = kwargs.get('silent', False)
        # domain
        self.domain = None
        # 强制重新部署
        self.redeploy = kwargs.get('redeploy', False)
        # 只部署这些机器
        self.deploy_host = kwargs.get('deploy_host', [])

        self.loadConf(file_path)

    def loadConf(self, file_path):
        '''
            加载配置文件
        '''
        config_obj = None
        with open(file_path) as df:
            config_obj = yaml.load(df)
        if not config_obj:
            raise ValueError('load %s fail' % file_path)

        self.domain = config_obj['domain']
        self.os_type = config_obj.get('os_type', 'ubuntu14')

        # 加载机器列表
        for res_name, params in config_obj.get('resources', {}).iteritems():
            resource = Resource(res_name, **params)
            self._resources[res_name] = resource

        # 加载机器分组列表
        for group_name, res_list in config_obj.get('resgroups', {}).iteritems():
            group = ResourceGroup(group_name, res_list, self._resources)
            self._resgroups[group_name] = group

        # 加载模块列表
        for module_name, params in config_obj.get('modules', {}).iteritems():
            params = params or {}
            module = NAME2MODULE[module_name](
                self._resources, self._resgroups, **params)
            self._modules[module_name] = module

        # 验证配置文件是否合法
        self.validate()

    def validate(self):
        """验证配置文件是否合法"""
        valid = True
        # 模块不能依赖优先级比自己低的模块
        for module_name, module in self._modules.iteritems():
            for dep in module.require:
                if self.module(dep).priority > module.priority:
                    LOG.error("[%s] cannot require a module[%s] with lower priority" % (
                        module_name, dep))
                    valid = False
        if not valid:
            raise ValueError('config file is not valid')

    def module(self, module_name):
        """
            @Brief 获取模块
            @Param module_name: 模块名称
            @Param allow_absent: 是否允许缺失,允许的话返回None
        """
        if module_name not in self._modules:
            return None
        return self._modules[module_name]

    def resource(self, res_name):
        '''
            获取资源
        '''
        if res_name not in self._resources:
            raise ValueError('undefined resource[%s]' % res_name)
        return self._resources[res_name]

    def resgroup(self, group_name):
        '''
            获取资源组
        '''
        if group_name not in self._resgroups:
            raise ValueError('undefined resource group[%s]' % group_name)
        return self._resgroups[group_name]

    def moduleReady(self, module_name):
        '''
            检查module的依赖是不是都部署完成了
        '''
        module = self._modules[module_name]
        ready = True
        for m in module.require:
            if not self._modules[m].deployed and not self._modules[m].check(self):
                logging.info('depend module %s is not deployed' % m)
                ready = False
                break
        return ready

    @property
    def modules(self): return self._modules

    @property
    def resources(self): return self._resources
