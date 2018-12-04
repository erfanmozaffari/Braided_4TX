#!/usr/bin/env python

import sys

def main(resultPath, eachTopo):
    inputPath = resultPath + "/" + eachTopo
    # inputPath= ../results/extractedDODAG/parents_log_topology_4_1_1.txt
    
    infile = open(inputPath, 'r')
    parentChildContainer = infile.readlines()
    infile.close()
    # determine number of nodes
    maxID=0
    for line in parentChildContainer:
        y = line.split()
        # currentNode: x firstParent: y
        if len(y) == 4:
            if int(y[1])>maxID:
                maxID=int(y[1])
            elif int(y[3])>maxID:
                maxID=int(y[3])
        # currentNode: x secondParent: z firstParent: y
        else:
            if int(y[1])>maxID:
                maxID=int(y[1])
            elif int(y[3])>maxID:
                maxID=int(y[3])
            elif int(y[5])>maxID:
                maxID=int(y[5])


    # this array keeps list of children for each mote. each mote's ID is array's index
    #childrenList = [-1 for i in range(maxID)]
    childrenList = []
    for i in range(maxID):
        childrenList.append([-1])

    # finding sink
    # node ID which is not appeared, is sink
    sink=0
    for line in parentChildContainer:
        y = line.split()
        childrenList[int(y[1])-1]=y[1]

    for i in range(maxID):
        if childrenList[i]==[-1]:
            childrenList[i]=[str(i+1)]
            sink=i+1
            break

    '''
    # DODAG matrix: 
    # collomn is parent and row is children, 
    # value is number of packets generated per slotframe(traffic demand) : defualt is 1
    '''
    pktsPerSlotframe = 1
    bestParentIdentifier = 10
    secondParentIdentifier = 20
    dodagMatrix = [[0 for i in range(maxID)] for j in range(maxID)]
    for line in parentChildContainer:
        y = line.split()
        if len(y) == 4:
            # node only has preferred parent
            # reinitialize parent and second parent
            for i in range(maxID):
                dodagMatrix[int(y[1])-1][i]=0
            # best parent
            dodagMatrix[int(y[1])-1][int(y[3])-1]=pktsPerSlotframe+bestParentIdentifier
        else:
            # node has both preferred and second parent
            # reinitialize parent and second parent
            for i in range(maxID):
                dodagMatrix[int(y[1])-1][i]=0
            # best parent
            dodagMatrix[int(y[1])-1][int(y[5])-1]=pktsPerSlotframe+bestParentIdentifier
            # second parent
            dodagMatrix[int(y[1])-1][int(y[3])-1]=pktsPerSlotframe+secondParentIdentifier

    # write dodagMatrix to file
    fileName  ="dodag_" 
    # remove "parents_log_" with "dodag_" in "parents_log_topology_4_1_1.txt"
    fileName += eachTopo[12:]
    outputPath  = resultPath + "/" + fileName
    # outputPath= ../results/extractedDODAG/dodag_topology_4_1_1.txt

    # write to file
    outfile = open(outputPath, 'w')
    outfile.write(str(maxID))
    outfile.write(str('\n'))
    for i in range(maxID):
        for j in range(maxID):
            outfile.write(str(dodagMatrix[i][j]))
            outfile.write(' ')
        outfile.write('\n')
    outfile.close()


if __name__ == "__main__":
    main(resultPath, eachTopo)