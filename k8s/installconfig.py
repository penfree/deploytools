#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from fabric.api import env
from fabric.state import output as output_level
import yaml
from collections import namedtuple

HostInfo = namedtuple('HostInfo', 'hostname,ip')


class InstallConfig(object):

    def __init__(self, k8s_config={}, ssh_config={}):
        self.k8s_config = k8s_config
        self.ssh_config = ssh_config
    
    @property
    def DockerComposeVersion(self):
        return self.k8s_config.get('dockerComposeVersion')
    
    @property
    def NetworkGateway(self):
        return self.k8s_config.get('networkGateway')

    @property
    def SvcSubnet(self):
        return self.k8s_config.get('svcSubnet')

    @property
    def DockerVersion(self):
        return self.k8s_config.get('dockerVersion')

    @property
    def ApiDNSName(self):
        return self.k8s_config['apiDNSName']

    @property
    def K8sVersion(self):
        return self.k8s_config.get('k8sVersion')

    @property
    def Interface(self):
        '''
            @Brief: kubernates运行的主网卡
        '''
        return self.k8s_config['interface']

    @property
    def ApiHAPort(self):
        '''
            @Brief: 负载均衡的api server端口
        '''
        return self.k8s_config.get('apiHAPort', 8443)
    
    @property
    def Token(self):
        return self.k8s_config.get('token')
    
    @property
    def TokenHash(self):
        return self.k8s_config.get('tokenHash')

    @property
    def ImagePath(self):
        '''
            @Brief: 打包的docker镜像路径
        '''
        return self.k8s_config['imagePath']

    @property
    def Master1(self):
        '''
            @Brief: 目前必须指定3个master
        '''
        return HostInfo(hostname=self.k8s_config['master1']['hostname'], ip=self.k8s_config['master1']['ip'])

    @property
    def Master2(self):
        return HostInfo(hostname=self.k8s_config['master2']['hostname'], ip=self.k8s_config['master2']['ip'])

    @property
    def Master3(self):
        return HostInfo(hostname=self.k8s_config['master3']['hostname'], ip=self.k8s_config['master3']['ip'])

    @property
    def VirtualIP(self):
        '''
            @Brief: 用于HA的虚拟IP
        '''
        return self.k8s_config['virtualIP']

    @property
    def PodSubnet(self):
        '''
            Pod网络
        '''
        return self.k8s_config.get('podSubnet', '10.244.0.0/16')

    @property
    def Slaves(self):
        '''
            @Brief: 所有的slave, ip的数组
        '''
        return self.k8s_config.get('slaves', [])

    @property
    def SSHUser(self):
        '''
            @Brief: ssh登录所有机器的用户名, 必须有sudo权限
        '''
        return self.ssh_config['user']

    @property
    def SSHIdentityFile(self):
        '''
            @Brief: ssh登录机器的证书，可选
        '''
        return self.ssh_config.get('identityFile')

    @property
    def SSHPassword(self):
        '''
            @Brief: ssh登录机器用的密码，可选，密码和证书都不提供时会提示输入密码
        '''
        return self.ssh_config.get('password')

    @property
    def Gateway(self):
        '''
            @Brief: gateway
        '''
        return self.ssh_config.get('gateway')
    
    def initFabric(self, verbose=True):
        '''
            @Brief: 初始化fabric连接信息
        '''
        if not verbose:
            output_level['status'] = False
            output_level['stdout'] = False
        
        env.user = self.SSHUser
        if self.SSHIdentityFile:
            env.key_filename = self.SSHIdentityFile
        if self.SSHPassword:
            env.password = self.SSHPassword
        if self.Gateway:
            env.gateway = self.Gateway
    
    def getAllHosts(self):
        '''
            @Brief: 获取所有机器的ip
        '''
        host_list = [self.Master1.ip, self.Master2.ip, self.Master3.ip]
        host_list.extend(self.Slaves)
        return host_list

    def getMasters(self):
        '''
            @Brief: 获取所有master的IP
        '''
        host_list = [self.Master1.ip, self.Master2.ip, self.Master3.ip]
        return host_list

    @classmethod
    def loadConfig(self, config_file):
        '''
            @Brief: 加载配置文件
        '''
        with open(config_file) as df:
            config_obj = yaml.load(df)
        return InstallConfig(config_obj['k8s'], config_obj['ssh'])
