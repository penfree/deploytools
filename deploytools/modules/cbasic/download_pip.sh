#!/bin/bash
packages=`cat pip.yaml | grep -v '\-\-\-' | grep '\-' | awk '{print $NF}'`

pip2pi ../pypi/repo/  $packages -n
