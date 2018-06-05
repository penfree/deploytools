#!/bin/bash
echo "clean toolset"
docker ps -a | grep Exit | grep toolset | awk '{print $1}' | xargs -i docker rm {}
echo "clean pause-amd64"
docker ps -a | grep Exit | grep pause-amd64 | awk '{print $1}' | xargs -i docker rm {}
echo "clean dangling volume"
docker volume rm $(docker volume ls -qf dangling=true)
echo "clean dangling images"
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
echo "clean containers"
docker ps -f status=exited | grep -E "buildsearch|builddatahub|matchpatient" | grep "Exited ([0-9]\+) [0-9]\+ weeks ago" | awk '{print $1}'  | xargs -i echo {}
docker ps -f status=exited | grep -E "buildsearch|builddatahub|matchpatient" | grep "Exited ([0-9]\+) [0-9]\+ months ago" | awk '{print $1}'  | xargs -i echo {}
