#!/bin/bash

# make all files and folders unlocked
currentUser=`who | awk '{print $1}'`
path="../${dirName[0]}"
# args:   "openwsn" "../results"
chown -R $currentUser: "results"