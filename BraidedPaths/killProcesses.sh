#!/bin/bash

# kill processes

sudo kill -9 `ps -aef | grep 'runBraidedPath' | grep -v grep | awk '{print $2}'`
sudo kill -9 `ps -aef | grep 'run_openwsn' | grep -v grep | awk '{print $2}'`
sudo kill -9 `ps -aef | grep 'pathTopo' | grep -v grep | awk '{print $2}'`

# make all files and folders unlocked
currentUser=`who | awk '{print $1}'`
path="../${dirName[0]}"
# args:   "openwsn" "../results"
chown -R $currentUser: $path