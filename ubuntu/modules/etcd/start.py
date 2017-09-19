#!/usr/bin/env python
# encoding=utf8

""" The etcd start script
    Author: lipixun
    Created Time : Tue 12 Jan 2016 07:42:50 PM CST

    File Name: start.py
    Description:

"""

import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import pwd
import prctl
import signal
import socket
import subprocess

def prestart():
    """The pre-start action
    """
    prctl.set_pdeathsig(signal.SIGKILL)

if __name__ == '__main__':

    from argparse import ArgumentParser

    def getArguments():
        """Get the arguments
        """
        parser = ArgumentParser(description = 'The etcd start script')
        parser.add_argument('--data-dir', dest = 'dataDir', help = 'The data dir')
        subParsers = parser.add_subparsers(dest = 'action')
        # Singleton
        singletonParser = subParsers.add_parser('singleton')
        # Cluster
        clusterParser = subParsers.add_parser('cluster')
        clusterParser.add_argument('--cluster', dest = 'cluster', required = True, help = 'The cluster name')
        clusterParser.add_argument('--discovery-domain', dest = 'discoveryDomain', required = True, help = 'The discovery domain')
        # Done
        return parser.parse_args()

    def addUrlParameters(args):
        """Add url parameters
        """

    def main():
        """The main entry
        """
        args = getArguments()
        # Check
        if args.action == 'singleton':
            # The singleton mode
            print '[Etcd Bootup] Config etcd in singleton model'
            etcdArgs = []
            if args.dataDir:
                etcdArgs.extend(('--data-dir', args.dataDir))
            hostname = socket.gethostname()
            etcdArgs.extend(('--listen-client-urls', 'http://%s:2379' % hostname))
            etcdArgs.extend(('--advertise-client-urls', 'http://%s:2379' % hostname))
        else:
            # The cluster mode
            print '[Etcd Bootup] Config etcd in cluster mode with cluster [%s] discovery domain [%s]' % (args.cluster, args.discoveryDomain)
            etcdArgs = [
                    '--name', socket.gethostname(),
                    '--discovery-srv', args.discoveryDomain,
                    '--initial-cluster-token', args.cluster,
                    '--initial-cluster-state', 'new'
                    ]
            if args.dataDir:
                etcdArgs.extend(('--data-dir', args.dataDir))
            hostname = socket.gethostname()
            etcdArgs.extend(('--listen-client-urls', 'http://%s:2379' % hostname))
            etcdArgs.extend(('--listen-peer-urls', 'http://%s:2380' % hostname))
            etcdArgs.extend(('--advertise-client-urls', 'http://%s:2379' % hostname))
            etcdArgs.extend(('--initial-advertise-peer-urls', 'http://%s:2380' % hostname))
        # Run etcd
        print '[Etcd Bootup] Start etcd'
        try:
            process = subprocess.Popen([ '/opt/etcd/etcd' ] + etcdArgs, preexec_fn = prestart)
            exitCode = process.wait()
            print '[Etcd Bootup] Etcd exist with code [%s]' % exitCode
            return exitCode
        except KeyboardInterrupt:
            print '[Etcd Bootup] Interrupted'
            return 1

    sys.exit(main())

