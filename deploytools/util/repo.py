#!/usr/bin/env python
# coding=utf8
"""
# Author: f
# Created Time : Mon 18 Jan 2016 08:10:14 PM CST

# File Name: util/repo.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import os
from os.path import dirname, join, abspath
import shutil
import subprocess
import logging
LOG = logging.getLogger("util.repo")

TOP_DIR = dirname(dirname(abspath(__file__)))


def installPythonTar(tar_path, package_name):
    '''
        安装pyyaml
    '''
    package_status = subprocess.call('python -c "import %s"' % package_name, shell=True)
    if package_status == 0:
        LOG.warn("%s is already installed" % package_name)
        return True

    subprocess.check_output("mkdir -p /tmp/{package}; tar -xzf {tar_path} -C /tmp/{package}".format(package=package_name, tar_path=tar_path), shell=True)
    os.chdir('/tmp/%s' % package_name)
    subprocess.check_output("python setup.py install", shell=True)
    subprocess.check_output("rm -rf /tmp/pyyaml", shell=True)
    subprocess.check_output('python -c "import %s"' % package_name, shell=True)
    return True


def ensureRequirements():
    '''
        检查fabric的安装状态
    '''
    fabric_status = subprocess.call("fab --version", shell=True)
    if fabric_status != 0:
        LOG.warn("fabric is not installed, trying to install")
        installPythonTar(os.path.join(TOP_DIR, 'packages', 'pip', 'Fabric-1.14.0.tar.gz'), 'fabric')

    pyyaml_status = subprocess.call('python -c "import yaml"', shell=True)
    if pyyaml_status != 0:
        LOG.warn("pyyaml is not installed, trying to install")
        installPythonTar(os.path.join(TOP_DIR, 'packages', 'pip', 'PyYAML-3.11.tar.gz'), 'pyyaml')
