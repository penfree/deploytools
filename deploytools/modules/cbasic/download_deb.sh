#!/bin/bash
packages=`cat deb.yaml | grep -v '\-\-\-' | grep '\-' | awk '{print $NF}'`
cd ../repository/repo

for package in $packages;
do
    ls | grep -E "^${package}_" > /dev/null
    if [[ $? == 0 ]];then
        echo "$package exists";
        continue
    fi
    for i in $(apt-rdepends $package|grep -v "^ ");
    do 
        sudo apt-get download $i ; 
    done
    echo "$package finished";
done

dpkg-scanpackages . | gzip > ./Packages.gz
