#!/usr/bin/env python

import sys
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt



def main(logPath, getDelayAndPdrFile, resultPath, algorithm, topoID):
	logPath = logPath + getDelayAndPdrFile
	infile  = open(logPath)
	stat    = infile.readlines()
	infile.close()

	pdr       		   = []
	tick_label		   = []     # flow Id
	delay     		   = []
	confidenceInterval = []

	for line in stat:
	    if '#' not in line:
	        sub = line.split()
	        pdr.append(sub[3])
	        tick_label.append(sub[0])
	        delay.append(float(sub[7])/1000)
	        confidenceInterval.append(float(float(sub[9])-float(sub[7]))/1000)

	# change list to numeric array
	pdr = np.asarray(pdr, dtype=np.float32)
	delay = np.asarray(delay, dtype=np.float32)
	confidenceInterval = np.asarray(confidenceInterval, dtype=np.float32)

	# x-coordinates of left sides of bars
	x_pos = [i for i, _ in enumerate(tick_label)]
	# or
	# x_pos = np.arange(len(tick_label))

	# *** plot PDR ***
	# plotting a bar chart
	plt.bar(x_pos, pdr, tick_label=tick_label, width=0.3, edgecolor='black', fill=True, hatch='...', 
		label=algorithm, color='w', align='center')

	# setting x and y axis range
	plt.ylim(0, 1)

	# naming the x axis
	plt.xlabel('Flow ID')
	# naming the y axis
	plt.ylabel('PDR')

	# giving a title to my graph
	plt.title('Packet Delivery Ratio')

	# function to show the plot
	plt.legend(loc='upper left', prop={'size':7}, bbox_to_anchor=(1,1))
	plt.tight_layout(pad=7)

	outputName   = resultPath + '/' + algorithm + "_PDR_" + str(topoID)
	outputFormat = outputName + ".tiff"
	plt.savefig(outputFormat)
	outputFormat = outputName + ".pdf"
	plt.savefig(outputFormat)

	# clear the figure
	plt.gcf().clear()


	# *** plot average e2e delay ***
	# plotting a bar chart
	plt.bar(x_pos, delay, tick_label=tick_label, width=0.3, yerr=confidenceInterval, ecolor='black', 
		fill=True, edgecolor='black', hatch='///', label=algorithm, color='w', align='center')

	# setting x and y axis range
	plt.ylim(0, 0.1)

	# naming the x axis
	plt.xlabel('Flow ID')
	# naming the y axis
	plt.ylabel('Average e2e Delay')

	# giving a title to my graph
	plt.title('Average End to End Delay')

	# function to show the plot
	plt.legend(loc=0)

	outputName   = resultPath + '/' + algorithm + "_DELAY_" + str(topoID)
	outputFormat = outputName + ".tiff"
	plt.savefig(outputFormat)
	outputFormat = outputName + ".pdf"
	plt.savefig(outputFormat)

	# clear the figure
	plt.gcf().clear()


if __name__ == "__main__":
    main(logPath, getDelayAndPdrFile, resultPath, algorithm, topoID)
