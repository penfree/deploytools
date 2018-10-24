#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from argparse import ArgumentParser
from fabric.api import local, settings, env

def getArgument():
    parser = ArgumentParser()
    parser.add_argument('-s', dest='source', required=True)
    parser.add_argument('-n', dest='num', default=4, type=int)
    return parser.parse_args()


def main():
    args = getArgument()
    print('%skbc label nodes s1.%s-bdmd.com bdmd.com/nodeinfra_ambari=allowed' % (args.source, args.source))
    print('%skbc label nodes s1.%s-bdmd.com bdmd.com/nodeinfra_mysql=allowed' % (args.source, args.source))
    print('%skbc label nodes s1.%s-bdmd.com bdmd.com/nodeinfra_nfs=allowed' % (args.source, args.source))
    print('%skbc label nodes s1.%s-bdmd.com bdmd.com/nodeinfra_redis=allowed' % (args.source, args.source))
    print('%skbc label nodes s1.%s-bdmd.com bdmd.com/nodeinfra-squid-dockercache=allowed' % (args.source, args.source))
    for i in range(1, 4):
        print('%skbc label nodes s%s.%s-bdmd.com bdmd.com/nodeinfra_mongodb=allowed' % (args.source, i, args.source))
    for i in range(1, args.num + 1):
        print('%skbc label nodes s%s.%s-bdmd.com bdmd.com/nodeinfra_elasticsearch=allowed' % (args.source, i, args.source))

main()
