import copy
import operator
import xlsxwriter
from DodagNode import DodagNode


class Dodag:
    def __init__(self):
        self.sink            = 1
        self.nodes           = []   # nodes of dodag
        self.leafs           = []   # leafs of dodag
        self.slotFrame       = []   # final slot frame
        self.numOfNodes      = 0    # Number of nodes in Dodag
        self.beginningOfFlow = []   # determine each flow starts on which time slot

    # destructor
    def __del__(self):
        self.nodes      = None
        self.leafs      = None
        self.slotFrame  = None
        self.numOfNodes = 0

    # read dodag from file
    def readDodag(self, filePath):

        dodagLines = ''
        try:
            with open(filePath, 'r') as inFile:
                dodagLines = inFile.readlines()
            inFile.close()
        except IOError:
            print("Could not read file: {0}".format(filePath))

        # read number of nodes
        if len(dodagLines[0].split()) == 1:
            tmp = dodagLines[0].split()
            self.numOfNodes = int(tmp[0])

        # allocate nodes
        for i in range(self.numOfNodes):
            self.nodes.append(DodagNode(i + 1))

        # Adjacency Matrix of DODAG
        adjacencyMatrix = [[0 for i in range(self.numOfNodes)] for j in range(self.numOfNodes)]

        # load dodag to matrix
        # inputs with number 20 means it is second parent + load
        # inputs with number 10 means it is best parent + load
        for i in range(self.numOfNodes):
            adjacencyMatrix[i] = dodagLines[i + 1].split()

        for i in range(self.numOfNodes):
            for j in range(self.numOfNodes):
                if int(adjacencyMatrix[i][j]) > 20:
                    self.nodes[i].secondParent = self.nodes[j]
                elif int(adjacencyMatrix[i][j]) > 10:
                    self.nodes[i].parent = self.nodes[j]
                    self.nodes[i].load = int(adjacencyMatrix[i][j]) - 10
                    self.nodes[j].NumChild += 1

        # find sink
        for i in range(self.numOfNodes):
            if not [True for x in adjacencyMatrix[i] if '1' in x]:
                self.sink = i + 1

        # find leafs
        for i in range(self.numOfNodes):
            if self.nodes[i].NumChild == 0:
                self.leafs.append(self.nodes[i])

        del adjacencyMatrix

    # get hop distance of each node
    def setHopDistanceOfNodes(self):
        # path from leaf to root
        path = []
        for i in range(len(self.leafs)):
            path.append(self.leafs[i])

            # Add all nodes to path which don't have hop Distance yet
            while path[-1].parent and path[-1].parent.hopDistance == -1:
                path.append(path[-1].parent)

            if not path[-1].parent:
                path[-1].hopDistance = 0
            else:
                path[-1].hopDistance = path[-1].parent.hopDistance + 1

            # set hop distance of nodes in the path
            for j in range(len(path) - 2, -1, -1):
                path[j].hopDistance = path[j + 1].hopDistance + 1
            #path.clear()
            del path[:]
            
    # helper Function: get node ID and return best and second parent
    def getParents(self, nodeID):

        bestParent = 0
        secondParent = 0
        isSink = False
        for node in self.nodes:
            if node.Id == nodeID:
                if node.parent:
                    isSink = node.parent.sink
                    bestParent = node.parent.Id
                if node.secondParent:
                    isSink = node.secondParent.sink
                    secondParent = node.secondParent.Id

        return isSink, bestParent, secondParent

    # insert Flow to main slot frame
    def insertFlowToSlotFrame(self, tempSlotFrame, flowSchedule, buffer, slotFrameLength):

        # compress the flows as much as possible: longest flow to shortest one
        # start from the beginning of the slotframe and look for the appropriate position of the flow. 
        # if there is a collision then shift the flow to start from the next timeslot. Do this operation till there is no conflict.
        # allocates the cells greedily for the set of links

        # flow ID
        fid                    = flowSchedule[0][0:flowSchedule[0].find("-")]
        lowerBoundTimeslot     = 0
        upperBoundTimeslot     = len(flowSchedule)
        rightPlaceToInsertFlow = False

        while upperBoundTimeslot < slotFrameLength and not rightPlaceToInsertFlow:
            checkNextPeriod = False
            for ch in range(len(tempSlotFrame)):
                if checkNextPeriod:
                    break
                for ts in range(lowerBoundTimeslot, upperBoundTimeslot):
                    if checkNextPeriod:
                        break
                    slotFrameNodeList  = []
                    tmp                = tempSlotFrame[ch][ts]
                    if not tempSlotFrame[ch][ts]:
                        pass
                    if '\n' in tempSlotFrame[ch][ts]:
                        # first Sender
                        slotFrameNodeList.append(tempSlotFrame[ch][ts][0:tmp.find("-")])
                        # second sender
                        slotFrameNodeList.append(tempSlotFrame[ch][ts][tmp.find("\n") + 1:tmp.find("-", tmp.find("-") + 1)])
                        # receiver
                        slotFrameNodeList.append(tempSlotFrame[ch][ts][tmp.find(">") + 1:tmp.find("\n")])
                    else:
                        # first Sender
                        slotFrameNodeList.append(tempSlotFrame[ch][ts][0:tmp.find("-")])
                        # receiver
                        slotFrameNodeList.append(tempSlotFrame[ch][ts][tmp.find(">") + 1:])
                    
                    for index in range(len(flowSchedule)):
                        flowNodeList = []
                        if '\n' in flowSchedule[index]:
                            # receiver
                            flowNodeList.append(flowSchedule[index][flowSchedule[index].find(">") + 1:flowSchedule[index].find("\n")])
                            # first sender
                            flowNodeList.append(flowSchedule[index][:flowSchedule[index].find("-")])
                            # second sender
                            flowNodeList.append(flowSchedule[index][flowSchedule[index].find("\n") + 1:flowSchedule[index].find("-", flowSchedule[index].find("-") + 1)])
                        else:
                            # receiver
                            flowNodeList.append(flowSchedule[index][flowSchedule[index].find(">") + 1:])
                            # first sender
                            flowNodeList.append(flowSchedule[index][:flowSchedule[index].find("-")])

                        # found conflict for the current position of the flow in slotframe
                        if any(i in flowNodeList for i in slotFrameNodeList) and ts >= lowerBoundTimeslot + index:
                            # increment the timeslot of the beginning of flow.
                            lowerBoundTimeslot += 1
                            upperBoundTimeslot  = lowerBoundTimeslot + len(flowSchedule)
                            checkNextPeriod     = True
                            break
            
            if not checkNextPeriod:
                rightPlaceToInsertFlow = True 

        self.beginningOfFlow[int(fid)-2] = lowerBoundTimeslot

        # insert to slotframe
        for ts in range(lowerBoundTimeslot, upperBoundTimeslot):
            for ch in range(len(tempSlotFrame)):
                if not tempSlotFrame[ch][ts]:
                    tempSlotFrame[ch][ts] = flowSchedule.pop(0)
                    break
        
    # calculate flow based sequential scheduling
    def flowBasedSequentialScheduling(self, slotFrameLength):

        tempSlotFrame = [['' for i in range(slotFrameLength)] for j in range(16)]
        # do not take into account sink mote (starting time slot of each flow)
        self.beginningOfFlow = [-1 for i in range(self.numOfNodes-1)]

        # sort nodes based on hop distance (inline): ascending order
        self.nodes.sort(key=operator.attrgetter('hopDistance'), reverse=True)
        
        # get schedule of each flow
        for node in self.nodes:
            if node.hopDistance > 0:
                # *** as we traverse a node, schedule the link and write it to "flowSchedule" then push its receivers to the "nodekeeper",
                # *** then pop from "nodekeeper" as a sender and schedule its link and push the receivers. do the same till reach the sink
                flowSchedule = []
                nodeKeeper = []
                sinkID = 0
                # best parent
                flowSchedule.append(str(node.Id) + "->" + str(node.parent.Id))
                nodeKeeper.append(node.parent.Id)
                # second parent
                if node.secondParent:
                    #secondary parent
                    flowSchedule.append(str(node.Id) + "->" + str(node.secondParent.Id))
                    # primary parent
                    flowSchedule.append(str(node.Id) + "->" + str(node.parent.Id))
                    # secondary parent
                    flowSchedule.append(str(node.Id) + "->" + str(node.secondParent.Id))
                    nodeKeeper.append(node.secondParent.Id)
                else:
                    flowSchedule.append(str(node.Id) + "->" + str(node.parent.Id))
                    flowSchedule.append(str(node.Id) + "->" + str(node.parent.Id))
                    flowSchedule.append(str(node.Id) + "->" + str(node.parent.Id))
                
                while nodeKeeper:
                    if int(nodeKeeper[0]) == self.sink:
                        break
                    # check to know are we in the last hop to sink or not
                    lastHop = False
                    moteId = nodeKeeper.pop(0)
                    isParentSink, bestParent, secondParent = self.getParents(int(moteId))
                    bestParentCell = str(moteId) + "->" + str(bestParent)
                    secondParentCell = str(moteId) + "->" + str(secondParent)
                    if bestParent == self.sink:
                        lastHop = True

                    # check last hop to the sink
                    if isParentSink and bestParent != 0 and bestParentCell not in flowSchedule[0]:
                        flowSchedule.append(bestParentCell)
                    if isParentSink and secondParent != 0 and secondParentCell not in flowSchedule[0]:
                        flowSchedule.append(secondParentCell)

                    # intermediate nodes
                    if bestParent != 0 and bestParentCell not in flowSchedule:
                        flowSchedule.append(bestParentCell)
                        if bestParent not in nodeKeeper:
                            nodeKeeper.append(bestParent)
                    if secondParent != 0 and secondParentCell not in flowSchedule:
                        # secondary parent
                        flowSchedule.append(secondParentCell)
                        # primary parent
                        flowSchedule.append(bestParentCell)
                        # secondary parent
                        flowSchedule.append(secondParentCell)
                        if secondParent not in nodeKeeper:
                            nodeKeeper.append(secondParent)
                    else:
                        flowSchedule.append(bestParentCell)
                        flowSchedule.append(bestParentCell)
                        flowSchedule.append(bestParentCell)

                # compress the flow: set shared cells
                i = 0
                flowScheduleLength = len(flowSchedule)
                while(i<flowScheduleLength):
                    senderID = int(flowSchedule[i][0:flowSchedule[i].find("-")])
                    receiverID = int(flowSchedule[i][flowSchedule[i].find(">")+1:])
                    for j in range(i+1, len(flowSchedule)):
                        if senderID != int(flowSchedule[j][0:flowSchedule[j].find("-")]) and \
                                receiverID == int(flowSchedule[j][flowSchedule[j].find(">")+1:]):
                            flowSchedule[i] += "\n" + flowSchedule[j]
                            flowSchedule.pop(j)
                            flowScheduleLength -= 1
                            break
                    i += 1

                # insert the flow schedule to main slotFrame
                # compress the flows as much as possible: shortest flow to longest one
                # pop each cell of flowSchedule and traverse from end of slotFrame till find a conflict slot, then sechedule the cell to next timeSlot
                self.insertFlowToSlotFrame(tempSlotFrame, flowSchedule, buffer, slotFrameLength)

        # delete empty slots of temp slotframe: find number of slots and channels used to schedule cells
        maxSlot = 0
        maxChannel = 0
        for channel in range(len(tempSlotFrame)):
            for slot in range(len(tempSlotFrame[channel])):
                if tempSlotFrame[channel][slot]:
                    maxSlot = slot if slot > maxSlot else maxSlot
                    maxChannel = channel if channel > maxChannel else maxChannel
        # copy optimized slot frame
        for channel in range(maxChannel + 1):
            self.slotFrame.append([])
            for slot in range(maxSlot + 1):
                self.slotFrame[channel].append(tempSlotFrame[channel][slot])

    # print scheduling
    def exportScheduling(self, workbook, worksheet):
        
        cell_format = workbook.add_format()

        cell_format.set_align('center')
        cell_format.set_align('vcenter')
        cell_format.set_border(2)

        worksheet.set_row(0, 50)

        # row and column type
        worksheet.write(0,0,'slot\n-----------\nchannel', cell_format)
        # timeslot offset
        for col in range(len(self.slotFrame[0])):
            worksheet.write(0, col+1, col, cell_format)
        # channel offset
        for row in range(len(self.slotFrame)):
            worksheet.write(row+1, 0, row, cell_format)
        # scheduling
        for row in range(len(self.slotFrame)):
            worksheet.set_row(row+1, 35)
            for col in range(len(self.slotFrame[0])):
                worksheet.write(row+1, col+1, self.slotFrame[row][col], cell_format)


    # write to file
    def writeScheduling(self, scheduleFileName, startFlowFileName):
        try:
            outFile = open(scheduleFileName, 'w')
        except IOError:
            print("Could not open file: {0}".format(scheduleFileName))

        CELLTYPE_TX = 1
        CELLTYPE_RX = 2
        SHARED = 1
        AnyCastAddr = 0

        outFile.write('#slot cellType shared channel neighbor\n')
        
        for node in self.nodes:
            # count number of cells to be scheduled per node
            numOfCells = 0
            for channel in range(len(self.slotFrame)):
                for slot in range(len(self.slotFrame[channel])):
                    if '\n' not in self.slotFrame[channel][slot]:
                        # sender
                        sender = self.slotFrame[channel][slot][0:self.slotFrame[channel][slot].find("-")]
                        receiver = self.slotFrame[channel][slot][self.slotFrame[channel][slot].find(">") + 1:]
                        if str(node.Id) == sender or str(node.Id) == receiver:
                            numOfCells += 1
                    # shared cells
                    elif '\n' in self.slotFrame[channel][slot]:
                        # senders
                        firstSender = self.slotFrame[channel][slot][0:self.slotFrame[channel][slot].find("-")]
                        tmp = self.slotFrame[channel][slot]
                        secondSender = tmp[tmp.find("\n") + 1:tmp.find("-", tmp.find("-") + 1)]
                        receiver = self.slotFrame[channel][slot][self.slotFrame[channel][slot].find(">") + 1:self.slotFrame[channel][slot].find("\n")]
                        if str(node.Id) == firstSender or str(node.Id) == secondSender or str(node.Id) == receiver:
                            numOfCells += 1

            if node.parent and node.secondParent:
                outFile.write('{0} {1} {2} {3}\n'.format(node.Id, numOfCells, node.parent.Id, node.secondParent.Id))
            elif node.parent:
                outFile.write('{0} {1} {2}\n'.format(node.Id, numOfCells, node.parent.Id))
            else:
                outFile.write('{0} {1}\n'.format(node.Id, numOfCells))

            # write cell status
            for channel in range(len(self.slotFrame)):
                for slot in range(len(self.slotFrame[channel])):
                    if self.slotFrame[channel][slot]:
                        # dedicated cells
                        if '\n' not in self.slotFrame[channel][slot]:
                            # sender
                            sender = self.slotFrame[channel][slot][0:self.slotFrame[channel][slot].find("-")]
                            receiver = self.slotFrame[channel][slot][self.slotFrame[channel][slot].find(">") + 1:]
                            if node.Id == int(sender):
                                outFile.write('{0} {1} {2} {3} {4}\n'.format(slot, CELLTYPE_TX, SHARED - 1, channel, receiver))
                            # receiver
                            elif node.Id == int(receiver):
                                outFile.write('{0} {1} {2} {3} {4}\n'.format(slot, CELLTYPE_RX, SHARED - 1, channel, sender))
                        # shared cells
                        elif '\n' in self.slotFrame[channel][slot]:
                            # senders
                            firstSender = self.slotFrame[channel][slot][0:self.slotFrame[channel][slot].find("-")]
                            tmp = self.slotFrame[channel][slot]
                            secondSender = tmp[tmp.find("\n") + 1:tmp.find("-", tmp.find("-") + 1)]
                            receiver = self.slotFrame[channel][slot][self.slotFrame[channel][slot].find(">") + 1:self.slotFrame[channel][slot].find("\n")]
                            if node.Id == int(firstSender) or node.Id == int(secondSender):
                                outFile.write('{0} {1} {2} {3} {4}\n'.format(slot, CELLTYPE_TX, SHARED - 1, channel, receiver))
                            # receiver
                            elif node.Id == int(receiver):
                                outFile.write('{0} {1} {2} {3} {4}\n'.format(slot, CELLTYPE_RX, SHARED, channel, AnyCastAddr))

        outFile.close()

        try:
            outFile = open(startFlowFileName, 'w')
        except IOError:
            print("Could not open file: {0}".format(startFlowFileName))

        for i in range(len(self.beginningOfFlow)):
            outFile.write('{0} {1}\n'.format(i+2, self.beginningOfFlow[i]))

        outFile.close()