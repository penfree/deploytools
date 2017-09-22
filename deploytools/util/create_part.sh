#!/bin/bash
while [[ $# -gt 0 ]];do
    DEV=$1
    shift

    #create gpt label
    parted -s $DEV mklabel gpt
    if [[ $? != 0 ]];then
      echo "make gpt failed";
      exit 1
    fi

    #make part
    parted -s $DEV -- mkpart primary 1049k -1
    if [[ $? != 0 ]];then
      echo "make part failed";
      exit 1
    fi

    #make filesystem
    PART="${DEV}1"
    mkfs.ext4  -F $PART
    if [[ $? != 0 ]];then
      echo "make filesystem failed";
      exit 1
    fi

    #get uuid
    UUID=`blkid | grep $PART | sed 's/.*UUID="//' | sed 's/".*//'`
    echo "UUID is $UUID"

    #mount disk
    DIRECTORY="/mnt/disk${DEV##*/dev/sd}"
    mkdir -p $DIRECTORY
    mount -t ext4  $PART $DIRECTORY

    grep $UUID /etc/fstab >/dev/null
    if [[ $? == 0 ]];then
      echo "uuid is already is in /etc/fstab" && exit 1
    fi

    echo "UUID=$UUID       $DIRECTORY      ext4    defaults        0       2" >> /etc/fstab
done
