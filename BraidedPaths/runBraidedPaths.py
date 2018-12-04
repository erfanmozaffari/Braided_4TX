#!/usr/bin/env python

import os
import sys
import shutil
import subprocess

stat_plotDir = os.path.join(os.path.dirname(sys.path[0]), 'stats_plots')
schedDir     = os.path.join(os.path.dirname(sys.path[0]), 'longestToShortestScheduler')
sys.path.insert(0, stat_plotDir)
sys.path.insert(0, schedDir)

from topo_dodag_stats_plots import retreiveStats
from topo_dodag_stats_plots import perTopoPlot
from topo_dodag_stats_plots import extractDodag_fw
from longestToShortestScheduler import scheduler


# variables
numMinimalCellsAndRxSerial=6
MSPERSLOT=15
# simulation period in seconds
simulationTime=2600
# slot frame size
slotFrameLength=101
# first parent and second parent are logged in this file
parentContainer='parentContainer.txt'
# BraidedPaths reads schedule from this file
BraidedPathsinput='scheduling_motes.txt'
# BraidedPaths output file name
BraidedPathsoutput='finalStat.txt'
# BraidedPaths reads start of each flow from this file
BraidedPathsstartOfFlows='startOfFlows.txt'
# BraidedPaths reads list of crashed motes from this file
BraidedPathsCrashedMotes='crashed_motes.txt'
# topologyGenerator.py and extractDODAG-fw(sw).py folder
topo_dodag_stats_plots='topo_dodag_stats_plots'
# creating folders
dirName=['results/topology_Dodag_Schedule', 'results/BraidedPathsresults', 'results/plots',
			'openwsnBraidedPaths/logs_Topology', 'openwsnDodagExtraction/logs_Topology']

# dictionary used instead of #ifdef
runModules = {'topoCreator': 'n', 'dodagExtraction': 'n', 'obtainDodag': 'n', 
				'calcSchedule': 'n', 'runOpenWSN': 'y', 'getStat': 'y', 'drawPlots': 'y'}

for i in dirName:
	if not os.path.exists(i):
		os.makedirs(i)
		print('{0} folder did not exits. Created now!'.format(i))
	else:
		print('{0} folder exits!'.format(i))


# list of directories in 'results/BraidedPathsresults'
topologies = [dI for dI in os.listdir(dirName[1]) if os.path.isdir(os.path.join(dirName[1],dI))]


# *** topology creator ***
if runModules['topoCreator'] == 'y':
	# remove files in results/topology_Dodag_Schedule
	for the_file in os.listdir(dirName[0]):
	    os.remove(os.path.join(dirName[0], the_file))
	#subprocess.call(['./topo_dodag_stats_plots/topologyGenerator.py', str(repeat=1), str(6), str(6), str(1), str(0.1), str(1), str('../'+dirName[0]), str(1)])


# *** openwsn dodag extraction ***
if runModules['dodagExtraction'] == 'y':
	for the_file in os.listdir(dirName[1]):
	    os.remove(os.path.join(dirName[1], the_file))

	# copy topologies from results/topology_Dodag_Schedule to openwsnDodagExtraction/logs_Topology
	for the_file in os.listdir(dirName[0]):
		shutil.copy2(os.path.join(dirName[0], the_file), dirName[4])
	# current Dir: openwsnDodagExtraction/logs_Topology
	os.chdir(dirName[4])

	# reads all .json files (topologies) in directory
	topos = [filename for filename in os.listdir('.') if filename.endswith ('.json')]

	#run openwsn for each topology to get parents log
	for eachTopo in topos:

		# run openwsn with given topology and specific duration
		subprocess.call(['./../run_openwsn.sh', str(eachTopo), str(simulationTime)])

		# create file name of parent logs via topology file name (remove '.json')
		targetFile='parents_log_{0}.txt'.format(eachTopo[:-5])
		# rename 'parentContainer.txt' to 'parents_log_topology_...'
		os.rename(parentContainer, targetFile)
		# move 'parents_log_topology_...' to results/topology_Dodag_Schedule
		shutil.move(targetFile, '../../{0}'.format(dirName[0]))

		print('{0} logs obtained!'.format(eachTopo))

	os.chdir('../../')



# *** obtain dodag ***
if runModules['obtainDodag'] == 'y':
	parents_log = [filename for filename in os.listdir(dirName[0]) if filename.startswith('parents_log')]

	#obtain dodag from parents log
	for eachTopo in parents_log:
		extractDodag_fw.main(dirName[0], eachTopo)
		print('{0} DODAG obtained!'.format(eachTopo))


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
	# removes files of openwsnBraidedPaths/logs_Topology
	for the_file in os.listdir(dirName[3]):
	    os.remove(os.path.join(dirName[3], the_file))
	
	# remove openvisualizer log file
	#if os.path.exists('openwsnBraidedPaths/openwsn-sw/software/openvisualizer/build/runui/openVisualizer.log'):
	#	os.remove('openwsnBraidedPaths/openwsn-sw/software/openvisualizer/build/runui/openVisualizer.log')
	if os.path.exists('openwsnBraidedPaths/openwsn-sw/software/openvisualizer/openwsnLogs.txt'):
		os.remove('openwsnBraidedPaths/openwsn-sw/software/openvisualizer/openwsnLogs.txt')
	
	# remove previous files in results/BraidedPathsresults
	for the_file in os.listdir(dirName[1]):
		if os.path.exists(os.path.join(dirName[1], the_file)) and os.path.isdir(os.path.join(dirName[1], the_file)):
			shutil.rmtree(os.path.join(dirName[1], the_file))

	# copy topologies from results/topology_Dodag_Schedule to openwsnBraidedPaths/logs_Topology
	for the_file in os.listdir(dirName[0]):
		shutil.copy2(os.path.join(dirName[0], the_file), dirName[3])

	#  current Dir: openwsnBraidedPaths/logs_Topology 
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
			os.rename(crashedMotes, BraidedPathsCrashedMotes)

		# rename scheduling file to 'scheduling_motes.txt'
		os.rename(scheduling, BraidedPathsinput)
		# rename start of flow file to 'startOfFlows.txt'
		os.rename(startOfFlow, BraidedPathsstartOfFlows)
		

		# reads 'scheduling_motes.txt' and topology with duration and runs openwsnBraidedPaths
		subprocess.call(['./../run_openwsn.sh', str(top), str(simulationTime)])
		
		# rename 'finalStat.txt' to 'stats_topology_5_1_1.txt'
		stats='stats_{0}.txt'.format(top[:-5])
		shutil.move('../openwsn-sw/software/openvisualizer/openwsnLogs.txt', stats)
		# rename 'scheduling_motes.txt' to base scheduling file name
		os.rename(BraidedPathsinput, scheduling)
		# rename 'startOfFlows.txt' to start of flow file name
		os.rename(BraidedPathsstartOfFlows, startOfFlow)

		print('{0} logs obtained!'.format(scheduling))
		# move all the files related to specific topology to BraidedPathsresults folder
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
		#shutil.copy2('../../{0}/{1}'.format(dirName[3], 'dodag_{0}.txt'.format(top[top.find('_')+1:top.find('_', top.find('_')+1)])), resultPath)
		if os.path.exists(crashedMotes):
			# rename crashed motes file to 'crashedMotes.txt'
			os.rename(BraidedPathsCrashedMotes, crashedMotes)
			shutil.copy2('../../{0}/{1}'.format(dirName[3], crashedMotes), resultPath)
			
		shutil.move('../../{0}/{1}'.format(dirName[3], startOfFlow), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], scheduling), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], stats), resultPath)
		shutil.move('../../{0}/{1}'.format(dirName[3], top), resultPath)
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
	getDelayAndPdrFile = 'delay_pdr.txt'
	algorithm          = 'BraidedPaths'

	for subDir in topologies:
		topoID  = int(subDir[subDir.find('_')+1:subDir.find('_',subDir.find('_')+1)])
		logPath = '{0}/{1}/'.format(dirName[1], subDir)	#resultPath
		perTopoPlot.main(logPath, getDelayAndPdrFile, dirName[2], algorithm, topoID)
		print('{0} plots done!'.format(subDir))



# unlock folders
subprocess.call(['./unlockFolders.sh'])
