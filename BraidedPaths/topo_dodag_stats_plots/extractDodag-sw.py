#!/usr/bin/env python

infile = open("parentContainer.txt", 'r')
parentChildContainer = infile.readlines()
infile.close()
# determine number of nodes
maxID=0
for line in parentChildContainer:
    y = line.split()
    if int(y[0][12:])>maxID:
        maxID=int(y[0][12:])
    elif int(y[1][12:])>maxID:
        maxID=int(y[1][12:])


# this array keeps list of children for each mote. each mote's ID is array's index
#childrenList = [-1 for i in range(maxID)]
childrenList = []
for i in range(maxID):
    childrenList.append([-1])

# finding sink
sink=0
for line in parentChildContainer:
    y = line.split()
    childrenList[int(y[0][12:])-1]=[y[0][12:]]

for i in range(maxID):
    if childrenList[i]==[-1]:
        childrenList[i]=[str(i+1)]
        sink=i+1
        break


# get list of each mote's children
for i in range(maxID):
    for line in parentChildContainer:
        y = line.split()
        if int(y[1][12:])==i+1:
            if y[0][12:] not in childrenList[i]:
                childrenList[i].append(y[0][12:])

for i in range(maxID):
    childrenList[i].pop(0)

'''
# DODAG matrix: 
# collomn is parent and row is children, 
# value is number of packets generated per slotframe(traffic demand) : defualt is 1
'''
pktsPerSlotframe = 1
dodagMatrix = [[0 for i in range(maxID)] for j in range(maxID)]
for i in range(maxID):
    for j in range(len(childrenList[i])):
        dodagMatrix[int(childrenList[i][j])-1][i]=pktsPerSlotframe

# write dodagMatrix to file
fileName="dodagMatrix_%d_Motes.txt" % (maxID)
outfile = open(fileName, 'w')
outfile.write(str(maxID))
outfile.write(str('\n'))
for i in range(maxID):
    for j in range(maxID):
        outfile.write(str(dodagMatrix[i][j]))
        outfile.write(' ')
    outfile.write('\n')
outfile.close()