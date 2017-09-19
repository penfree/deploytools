#!/bin/bash
vmname=$1
vmdir=$2
vboxmanage registervm $vmdir

if [[ $? != 0 ]];then
    echo "register vm failed" && exit 1
fi

vboxmanage modifyvm $vmname --vrde on

if [[ $? != 0 ]];then
    echo "open vrde failed" && exit 1
fi

read -p "Enter vrde port:" port

vboxmanage modifyvm $vmname --vrdeport $port

if [[ $? != 0 ]];then
    echo "set vrdeport failed" && exit 1
fi

read -p "Set memory:" memory
vboxmanage modifyvm $vmname --memory $memory
if [[ $? != 0 ]];then
    echo "set memory failed" && exit 1
fi

read -p "Set cpu:" cpu
vboxmanage modifyvm $vmname --cpus $cpu
if [[ $? != 0 ]];then
    echo "set cpu failed" && exit 1
fi

vboxmanage modifyvm $vmname --nic1 nat
if [[ $? != 0 ]];then
    echo "change network to nat failed" && exit 1
fi

vboxmanage startvm $vmname --type headless
if [[ $? != 0 ]];then
    echo "start vm failed" && exit 1
fi

read -p "sharedfolder path:" sharefolder
vboxmanage sharedfolder add $vmname --name "share" --hostpath $sharefolder --transient --automount

if [[ $? != 0 ]];then
    echo "add shared folder failed" && exit 1
fi
