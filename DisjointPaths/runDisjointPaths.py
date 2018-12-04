#!/usr/bin/env python

import os
import sys
import shutil
import subprocess

stat_plotDir = os.path.join(os.path.dirname(sys.path[0]), 'stats_plots')
schedDir     = os.path.join(os.path.dirname(sys.path[0]), 'longestToShortestScheduler')
sys.path.insert(0, stat_plotDir)
sys.path.insert(0, schedDir)

from stats_plots import retreiveStats
from stats_plots import perTopoPlot
from longestToShortestScheduler import scheduler

# variables
numMinimalCellsAndRxSerial=6
MSPERSLOT=15
# simulation period in seconds
simulationTime=2400
# slot frame size
slotFrameLength=101
# first parent and second parent are logged in this file
parentContainer='parentContainer.txt'
# DisjointPath reads schedule from this file
DisjointPathinput='scheduling_motes.txt'
# DisjointPath output file name
DisjointPathoutput='finalStat.txt'
# DisjointPath reads start of each flow from this file
DisjointPathstartOfFlows='startOfFlows.txt'
# DisjointPaths reads list of crashed motes from this file
DisjointPathsCrashedMotes='crashed_motes.txt'
#topologyGenerator.py and extractDODAG-fw(sw).py folder
stats_plots='stats_plots'
# creating folders
dirName=['results/topology_Dodag_Schedule', 'results/DisjointPathresults', 'results/plots',
		 'openwsnDisjointPathRPL/logs_Topology']

# dictionary used instead of #ifdef
runModules = {'calcSchedule': 'n', 'runOpenWSN': 'y', 'getStat': 'y', 'drawPlots': 'y'}

for i in dirName:
	if not os.path.exists(i):
		os.makedirs(i)
		print('{0} folder did not exits. Created now!'.format(i))
	else:
		print('{0} folder exits!'.format(i))


# list of directories in 'results/DisjointPathresults'
topologies = [dI for dI in os.listdir(dirName[1]) if os.path.isdir(os.path.join(dirName[1],dI))]


# *** calculateScheduling ***
if runModules['calcSchedule'] == 'y':
	dodag_logs = [filename for filename in os.listdir(dirName[0]) if filename.startswith('dodag')]

	# prepare to compile scheduler source code
	os.chmod('longestToShortestScheduler/scheduler.py', 0o777)
	os.chmod('longestToShortestScheduler/Dodag.py', 0o777)
	os.chmod('longestToShortestScheduler/DodagNode.py', 0o777)

	os.chdir('longestToShortestScheduler')
	# run scheduler to get scheduling for each dodag
	for dodag in dodag_logs:
		inputFile = '../' + dirName[0] + '/' + dodag
		# remove 'dodag_' from file name (write output to results/topology_Dodag_Schedule)
		output      = '../{0}/schedule_topology_{1}'.format(dirName[0], dodag[dodag.find('_')+1:dodag.find('_', dodag.find('_')+1)])
		startOfFlow = '../{0}/startOfFlow_topology_{1}'.format(dirName[0], dodag[dodag.find('_')+1:dodag.find('_', dodag.find('_')+1)])
		scheduler.main(inputFile, output, slotFrameLength, startOfFlow)
		print('{0} scheduling obtained!'.format(dodag))
	
	os.chdir('../')


# *** run openwsn ***
if runModules['runOpenWSN'] == 'y':
	# removes files of openwsnDisjointPathRPL/logs_Topology
	for the_file in os.listdir(dirName[3]):
	    os.remove(os.path.join(dirName[3], the_file))

	# remove openvisualizer log file
	if os.path.exists('openwsnDisjointPathRPL/openwsn-sw/software/openvisualizer/openwsnLogs.txt'):
		os.remove('openwsnDisjointPathRPL/openwsn-sw/software/openvisualizer/openwsnLogs.txt')

	# remove previous files in results/DisjointPathresults
	for the_file in os.listdir(dirName[1]):
		if os.path.exists(os.path.join(dirName[1], the_file)) and os.path.isdir(os.path.join(dirName[1], the_file)):
			shutil.rmtree(os.path.join(dirName[1], the_file))

	# copy topologies from results/topology_Dodag_Schedule to openwsnDisjointPathRPL/logs_Topology
	for the_file in os.listdir(dirName[0]):
		shutil.copy2(os.path.join(dirName[0], the_file), dirName[3])

	#  current Dir: openwsnDisjointPathRPL/logs_Topology 
	os.chdir(dirName[3])

	# reads all topology files in directory (gets files beginning with 'topology')
	topos = [filename for filename in os.listdir('.') if filename.startswith('topology')]

	for top in topos:
		# get file name of each scheduling file via topology files (remove '.json' from file name)
		scheduling   = 'schedule_{0}.txt'.format(top[0:top.find('_', top.find('_')+1)])
		# get file name of start of each flow file via topology files (remove '.json' from file name)
		startOfFlow  = 'startOfFlow_{0}.txt'.format(top[0:top.find('_', top.find('_')+1)])
		# get file name of crashed motes file via topology files (remove '.json' from file name)
		crashedMotes = 'crashedMotes_{0}.txt'.format(top[0:top.find('_', top.find('_')+1)])
		# copy scheduling of current topology to current directory
		shutil.copy2('../../{0}/{1}'.format(dirName[0], scheduling), os.getcwd())
		# copy start of flow of current topology to current directory
		shutil.copy2('../../{0}/{1}'.format(dirName[0], startOfFlow), os.getcwd())
		# copy crashed motes of current topology to current directory
		if os.path.exists('../../{0}/{1}'.format(dirName[0], crashedMotes)):
			shutil.copy2('../../{0}/{1}'.format(dirName[0], crashedMotes), os.getcwd())
			# rename crashed motes file to 'crashedMotes.txt'
			os.rename(crashedMotes, DisjointPathsCrashedMotes)
		# rename scheduling file to 'scheduling_motes.txt'
		os.rename(scheduling, DisjointPathinput)
		# rename start of flow file to 'startOfFlows.txt'
		os.rename(startOfFlow, DisjointPathstartOfFlows)

		# reads 'scheduling_motes.txt' and topology with duration and runs openwsnDisjointPathRPL
		subprocess.call(['./../run_openwsn.sh', str(top), str(simulationTime)])
		
		# rename 'finalStat.txt' to 'stats_topology_5_1_1.txt'
		stats='stats_{0}.txt'.format(top[:-5])
		shutil.move('../openwsn-sw/software/openvisualizer/openwsnLogs.txt', stats)
		# rename 'scheduling_motes.txt' to base scheduling file name
		os.rename(DisjointPathinput, scheduling)
		# rename 'startOfFlows.txt' to start of flow file name
		os.rename(DisjointPathstartOfFlows, startOfFlow)
		print('{0} logs obtained!'.format(scheduling))
		# move all the files related to specific topology to MCSresults folder
		resultPath = '../../{0}/{1}'.format(dirName[1], top[:-5])
		
		if not os.path.exists(resultPath):
			os.makedirs(resultPath)
			print('{0} folder did not exits. Created now!'.format(resultPath))
		else:
			print('{0} folder exits!'.format(resultPath))
		'''
		for the_file in os.listdir('../../{0}'.format(dirName[3])):
			shutil.move('../../{0}/{1}'.format(dirName[3], the_file), resultPath)
		'''
		
		#shutil.move('../../{0}/{1}'.format(dirName[3], 'dodag_{0}.txt'.format(top[top.find('_')+1:top.find('_', top.find('_')+1)])), resultPath)
		if os.path.exists(crashedMotes):
			# rename crashed motes file to 'crashedMotes.txt'
			os.rename(DisjointPathsCrashedMotes, crashedMotes)
			shutil.copy2('../../{0}/{1}'.format(dirName[3], crashedMotes), os.getcwd())
		shutil.move('../../{0}/{1}'.format(dirName[3], startOfFlow), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], scheduling), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], stats), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], top), resultPath)
	# current Directory: DisjointPaths
	os.chdir('../../')


# *** stats ***
if runModules['getStat'] == 'y':
	# now loop through the directories:
	for subDir in topologies:
		destPath = '{0}/{1}/'.format(dirName[1], subDir)
		# obtain sent and received packet logs
		statLog = [filename for filename in os.listdir('{0}/{1}'.format(dirName[1], subDir)) if filename.startswith('stats')]
		log = '{0}{1}'.format(destPath, statLog[0])
		retreiveStats.main(log,destPath,MSPERSLOT,numMinimalCellsAndRxSerial) 
		print('{0} statistics done!'.format(subDir))


# *** figures ***
if runModules['drawPlots'] == 'y':
	getDelayAndPdrFile='delay_pdr.txt'
	algorithm='DisjointPaths'

	for subDir in topologies:
		topoID  = int(subDir[subDir.find('_')+1:subDir.find('_',subDir.find('_')+1)])
		logPath = '{0}/{1}/'.format(dirName[1], subDir)	#resultPath
		perTopoPlot.main(logPath, getDelayAndPdrFile, dirName[2], algorithm, topoID)
		print('{0} plots done!'.format(subDir))


# unlock folders
subprocess.call(['./unlockFolders.sh'])
