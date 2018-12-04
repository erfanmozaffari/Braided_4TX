#!/bin/bash

# *** current Dir: logs_Topology ***

#compile openwsn
cd ./../openwsn-fw
scons --warn=no-all board=python toolchain=gcc oos_openwsn

#run simulaton
cd ./../openwsn-sw/software/openvisualizer
sudo scons runweb --sim  --pathTopo="../../../logs_Topology/$1" --duration=$2

#kill process manually
sudo kill -9 `ps -aef | grep 'pathTopo' | grep -v grep | awk '{print $2}'`