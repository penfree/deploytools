#!/usr/bin/env python
#coding=utf8
"""
# Author: f
# Created Time : Sat 31 Oct 2015 12:15:25 PM CST

# File Name: tool.py
# Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from functools import wraps
import StringIO
import logging
import os
import socket

def retry(retry_times = 1):
    '''
        任务执行失败时根据被修饰函数的返回值重试:
        非0值: 正常
        0: 异常
    '''
    def deco_retry(f):
        def wrapper(*args, **kwargs):
            max_retries = retry_times
            while max_retries >= 1:
                result = f(*args, **kwargs)
                if result:
                    return result
                else:
                    max_retries -= 1
                    if max_retries >= 1:
                        logging.warn("task failed, will retry, %d chance remained" % max_retries)
            return False
        return wrapper
    return deco_retry

def ping(ip, port):
    """
        @Brief ping 检查端口是否打开
        @Param ip:
        @Param port:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except:
        return False
