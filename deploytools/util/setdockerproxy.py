#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import platform
import os

# 创建目录
if not os.path.exists('/etc/systemd/system/docker.service.d'):
    os.makedirs('/etc/systemd/system/docker.service.d')

# 写入配置
with open('/etc/systemd/system/docker.service.d/http-proxy.conf', 'w') as df:
    print >>df, '[Service]'
    print >>df, 'Environment="HTTP_PROXY=http://192.168.50.12:3128/"'
    print >>df, 'Environment="NO_PROXY=localhost,127.0.0.0/8,192.168.50.0/24,192.168.10.0/24,192.168.60.0/24,dockerdist.bdmd.com"'

os.system('systemctl daemon-reload')
os.system('systemctl restart docker')

