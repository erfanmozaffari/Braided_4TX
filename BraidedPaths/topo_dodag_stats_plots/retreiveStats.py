#!/usr/bin/env python

import os
import sys
import math
from scipy import stats
import numpy as np
import scipy

sinkID = 0

'''
# packet log sample:
STAT_PK_TX |addr= 0003 |asn= 12270 |length= 63 |slotOffset= 11 |frequency= 20 |l2Dest= 02 |numTxAttempts= 1 |L3Src= 03 |L3Dest= 01 |L4Proto= IANA_UDP |SeqNum= 11 |l2Dsn= 4
STAT_PK_RX |addr= 0002 |asn= 12270 |length= 42 |slotOffset= 11 |frequency= 20 |l2Src= 03 |L3Src= 00 |L3Dest= 82 |L4Proto= IANA_ICMPv6_ECHO_REQUEST |SeqNum= 34436 |l2Dsn= 4
STAT_PK_TX |addr= 0002 |asn= 12271 |length= 63 |slotOffset= 12 |frequency= 21 |l2Dest= 01 |numTxAttempts= 1 |L3Src= 03 |L3Dest= 01 |L4Proto= IANA_UDP |SeqNum= 11 |l2Dsn= 68
STAT_PK_RX |addr= 0001 |asn= 12271 |length= 42 |slotOffset= 12 |frequency= 21 |l2Src= 02 |L3Src= 03 |L3Dest= 01 |L4Proto= IANA_UDP |SeqNum= 11 |l2Dsn= 68
'''

# *** Functions ***
# 95% confidence interval
# sem: Standard Error of Mean
def mean_confidence_interval(data):
    a = 1.0 * np.array(data)
    n = len(a)
    m = np.mean(a)
    h = 1.96 * scipy.stats.sem(a)
    return m, m - h, m + h

# check that the sent packet is received to next hop or not
def reachedNextHop(inputTx, fileName):
    infile = open(fileName, 'r')
    firstHandler = infile.readlines()
    infile.close()

    found = False
    j = 0
    while j < len(firstHandler):
        received = firstHandler[j].split()
        if ((received[0] == 'STAT_PK_RX') and (int(inputTx[24]) == int(received[22])) and   # sentDsn==rcvDsn
                                              (int(inputTx[12],16) == int(received[2],16)) and    # sentl2Dest==rcvaddr
                                              (int(inputTx[8])  == int(received[8])) and    # sentSlot==rcvSlot
                                              (int(inputTx[10]) == int(received[10]))):     # sentChannel==rcvChannel
            found = True
            break
        j += 1
    return found

# calculate jitter for each flow
def calculateJitter(perPktDelayArray, avgDelay):
    avgJitter = 0
    for i in range(len(perPktDelayArray)):
        if perPktDelayArray[i] > avgDelay:
            avgJitter += perPktDelayArray[i] - avgDelay
        else:
            avgJitter += avgDelay - perPktDelayArray[i]

    avgJitter = float(avgJitter)/len(perPktDelayArray)
    return avgJitter


# gets sent and received asn of a packet
# input: received packet,   output: sent packet from source
def getSentAndReceivedTime(data, fileName):
    pathToDagroot = []
    rcvdPkt       = data.split()
    pathToDagroot.append(int(rcvdPkt[2]))
    infile       = open(fileName, 'r')
    firstHandler = infile.readlines()
    infile.close()

    i                 = 0
    oneHopToSinkFound = False
    while i < len(firstHandler) and (not oneHopToSinkFound):
        currSentPkt = firstHandler[i].split()
        prevPkt     = currSentPkt
        if ((currSentPkt[0] == 'STAT_PK_TX') and (int(currSentPkt[8])  == int(rcvdPkt[8])) and   # sntTimeSlot==rcvTimeSlot
                                                 (int(currSentPkt[10]) == int(rcvdPkt[10])) and  # sntChannel==rcvChannel
                                                 (int(currSentPkt[16],16) == int(rcvdPkt[14],16)) and  # sntL3Src==rcvL3Src
                                                 (int(currSentPkt[18],16) == int(rcvdPkt[16],16)) and  # sntL3Dest==rcvL3Dest
                                                 (int(currSentPkt[22]) == int(rcvdPkt[20])) and  # sntSeqNum==rcvSeqNum
                                                 (int(currSentPkt[24]) == int(rcvdPkt[22])) and  # sntDsn==rcvDsn
                                                 (int(currSentPkt[4])  <= int(rcvdPkt[4]))):     # sntASN<=rcvASN
            oneHopToSinkFound = True
            pathToDagroot.insert(0, int(currSentPkt[2]))
            if int(currSentPkt[16],16) == int(currSentPkt[2],16):      # L3Src==addr
                return int(currSentPkt[4]), int(currSentPkt[14]), pathToDagroot
            else:
                j = i-1
                while j >= 0:
                    prevPkt = firstHandler[j].split()
                    if (prevPkt[0] == 'STAT_PK_TX' and (int(currSentPkt[16],16) == int(prevPkt[16],16)) and   # currSntL3Src==prevSntL3Src
                                                       (int(currSentPkt[18],16) == int(prevPkt[18],16)) and   # currSntL3Dest==prevSntL3Dest
                                                       (int(currSentPkt[22]) == int(prevPkt[22])) and   # currSntSeqNum==prevSntSeqNum
                                                       (int(currSentPkt[4])  >  int(prevPkt[4])) and    # currSntASN>prevSntASN
                                                       (reachedNextHop(prevPkt, fileName))):
                        currSentPkt = prevPkt

                        pathToDagroot.insert(0, int(currSentPkt[2],16))
                    j -= 1
        i += 1
    return int(currSentPkt[4]), int(currSentPkt[14]), pathToDagroot


# find path for the nodes which are found based on their ACK
def findPath(destPath ,moteID):
    logPath   = os.path.join(destPath, "finalStatSorted_asn.txt")
    infile    = open(logPath)
    stat_data = infile.readlines()
    infile.close()

    path = []
    currentMote = moteID
    for y in stat_data:
        if 'STAT_PK_TX' in y and 'IANA_UDP' in y:
            line = y.split()
            if int(line[2],16) == currentMote and int(line[16],16) == moteID:
                path.append(str(currentMote))
                currentMote = int(line[12],16)
                if currentMote == sinkID:
                    path.append(str(currentMote))
                    break
    return path
            


def main(logPath, destPath, slotDuration, numMinimalCells):
        
    global sinkID
    # ms per slot (here 15ms)
    MSPERSLOT    = slotDuration
    topologySize = 0
    pktLength    = 63*8 # packet size in bits
    
    # *** keep only related packets: STAT_PK_TX & STAT_PK_RX & STAT_ACK
    infile    = open(logPath)
    stat_data = infile.readlines()
    infile.close()
    outfile   = open('{0}finalStat_onlyDataPkt.txt'.format(destPath), 'w')
    for line in stat_data:
        if 'STAT_PK_TX' in line or 'STAT_PK_RX' in line:
            y = line.split()
            if int(y[11]) >= numMinimalCells:
                y = " ".join(y[3:])
                outfile.write(y)
                outfile.write('\n')
        elif 'STAT_ACK' in line:
            y = line.split()
            if 'fff' not in y[11]:
                y = " ".join(y[3:])
                outfile.write(y)
                outfile.write('\n')

    outfile.close()

    # *** sort packets based on their asn
    infile    = open('{0}finalStat_onlyDataPkt.txt'.format(destPath))
    stat_data = infile.readlines()
    infile.close()
    sortedData = sorted(stat_data, key=lambda x: int((x.split('|asn= ')[1]).split(' |')[0]))
    outfile    = open('{0}finalStatSorted_asn.txt'.format(destPath), 'w')
    for elem in sortedData:
        outfile.write(elem)
    outfile.close()

    # *** remove all the duplicated lines : some lines are exactly duplicated
    infile    = open('{0}finalStatSorted_asn.txt'.format(destPath))
    stat_data = infile.readlines()
    infile.close()
    outfile    = open('{0}finalStatSorted_noDup.txt'.format(destPath), 'w')
    for i, line in enumerate(stat_data):
        outfile.write(line)
        statSize = len(stat_data)
        while i + 1 < statSize:
            if stat_data[i+1] == line:
                del(stat_data[i+1])
                statSize -= 1
                i        -= 1
            i += 1
    outfile.close()
    
    # *** determine topology size
    infile                = open('{0}finalStatSorted_noDup.txt'.format(destPath), 'r')
    topoSize_sink_Handler = infile.readlines()
    infile.close()

    for line in topoSize_sink_Handler:
        y = line.split()
        if int(y[2],16) > topologySize:
            topologySize = int(y[2],16)

    # *** find sink moteID: node ID which is not appeared, is sink
    childrenList = [0 for i in range(topologySize)]
    for line in topoSize_sink_Handler:
        y = line.split()
        if y[0] == 'STAT_PK_TX' and y[20] == 'IANA_UDP':
            childrenList[int(y[2],16) - 1] = int(y[2],16)

    for i in range(topologySize):
        if childrenList[i] == 0:
            sinkID = i + 1
            break
    
    # *** delete duplicated sent and received packets
    infile       = open('{0}finalStatSorted_noDup.txt'.format(destPath), 'r')
    firstHandler = infile.readlines()
    infile.close()

    i = 0
    while i < len(firstHandler):
        y = firstHandler[i].split()
        # slots belonging to minimal cells and serial Rx are omitted. (here 6 slots)
        if y[0] != 'STAT_ACK':
            if y[0] == 'STAT_PK_RX' and int(y[2],16) == sinkID and y[18] != 'IANA_UDP':
                # remove duplicated received packets to sink. (layer 2, as we are receiving in layer 3)
                del firstHandler[i]
                i -= 1  # when you remove a line afterward lines index decreases one unit
        i += 1

    # remove duplicated received packets
    i = 0
    while i < len(firstHandler):
        y = firstHandler[i].split()
        if y[0] == 'STAT_PK_RX' and y[18] == 'IANA_UDP':
            j = i + 1
            while j < len(firstHandler):
                x = firstHandler[j].split()     #ASN             #L3Src            #seqNum           #IANA_UDP
                if x[0] == 'STAT_PK_RX' and y[4] != x[4] and y[14] == x[14] and y[20] == x[20] and x[18] == y[18]:
                    del firstHandler[j]
                    j -= 1  # when you remove a line afterward lines index decreases one unit
                j += 1
        i += 1

    # each TX must have one RX. if it does not match then remove it
    i = 0
    while i < len(firstHandler):
        y = firstHandler[i].split()
        if y[0] == 'STAT_PK_TX':
            l2DsnTx  = int(y[24])
            timeSlot = int(y[8])
            channel  = int(y[10])
            nextNode = int(y[12],16)
            j = 0
            found = False
            while j < len(firstHandler):
                x = firstHandler[j].split()
                if ((x[0] == 'STAT_PK_RX') and (l2DsnTx  == int(x[22])) and
                                               (nextNode == int(x[2],16)) and
                                               (timeSlot == int(x[8])) and
                                               (channel  == int(x[10]))):
                    found = True
                    break
                j += 1
            if not found:
                del firstHandler[i]
                i -= 1
        i += 1

    rmvDupsHandler = open('{0}finalStatSorted.txt'.format(destPath), 'w')
    for i in range(len(firstHandler)):
        rmvDupsHandler.write(firstHandler[i])
    rmvDupsHandler.close()
    
    # *** Get sent and received time of a packet
    # per packet delay for each node
    eachNodesPktDelay = [[] for j in range(topologySize)]
    # per node path to the sink
    pathToSink        = [[] for i in range(topologySize)]

    with open('{0}finalStatSorted.txt'.format(destPath)) as rcvdPkts:
        sentReceived_timeFile = open('{0}pkts_snt_rcvd_time.txt'.format(destPath), 'w')
        sentReceived_timeFile.write("#Source PktID NumTxAttempts SenderASN ReceiverASN calculatedDelay\n")
        for rcvdLine in rcvdPkts:
            x = rcvdLine.split()                 # addr == sinkID
            if (x[0] == 'STAT_PK_RX') and (int(x[2],16) == sinkID) and x[18] == 'IANA_UDP':
                senderASN, numTxAttempt, tempPath = getSentAndReceivedTime(rcvdLine, '{0}finalStatSorted.txt'.format(destPath))
                currentDelay = (int(x[4]) - senderASN + 1) * MSPERSLOT
                eachNodesPktDelay[int(x[14],16)-1].append(currentDelay)
                if pathToSink[int(x[14],16) - 1] != tempPath and len(pathToSink[int(x[12],16) - 1]) <= len(tempPath):
                    pathToSink[int(x[14],16) - 1] = tempPath
                sentReceived_timeFile.write(" {:<7}{:<6}{:<14}{:<10}{:<12}{:<15}\n".format(int(x[14],16),            # source Addr
                                                                                              x[20],              # packet ID
                                                                                              numTxAttempt,       # number of Tx attempts
                                                                                              senderASN,          # sender's ASN
                                                                                              x[4],               # receiver's ASN
                                                                                              currentDelay        # calculated Delay
                                                                                          ))
        sentReceived_timeFile.close()
    rcvdPkts.close()

    # *** resolve misbehavior of log analyser (does not print last hop received packet)
    #STAT_PK_TX |addr= 0003 |asn= 21118 |length= 62 |slotOffset= 9 |frequency= 21 |l2Dest= 01 |numTxAttempts= 2 |L3Src= 05 |L3Dest= 01 |L4Proto= IANA_UDP |SeqNum= 8 |l2Dsn= 110 |frameType= IEEE154_TYPE_DATA |txpower= 1
    #STAT_ACK |addr= 0003 |asn= 21118 |status= RCVD |l2addr= 141592cc00000001
    # work based on received ack
    infile     = open('{0}finalStatSorted_asn.txt'.format(destPath), 'r')
    statFile   = infile.readlines()
    infile.close()

    infile     = open('{0}pkts_snt_rcvd_time.txt'.format(destPath), 'r')
    checkDelay = infile.readlines()
    infile.close()

    sentReceived_File = open('{0}pkts_snt_rcvd_time.txt'.format(destPath), 'a')


    for index, line in enumerate(statFile):
        if 'STAT_ACK' in line and 'RCVD' in line:
            ack               = line.split()
            i                 = index if i < 1 else index-1
            oneHopToSinkFound = False
            printedOut        = False
            insertedBefore    = False
            while i < len(statFile) and (not oneHopToSinkFound):
                currSentPkt = statFile[i].split()
                prevPkt     = currSentPkt
                if ((currSentPkt[0] == 'STAT_PK_TX') and (int(currSentPkt[12], 16)   == int(ack[8][10:], 16)) and #sntl2Dest==ackl2addr
                                                            (int(currSentPkt[2], 16) == int(ack[2], 16)) and      # sntAddr==ackAddr
                                                            (currSentPkt[20]         == 'IANA_UDP') and           # sntTimeSlot==ackTimeSlot                         
                                                            (int(ack[8][10:], 16)    == sinkID) and               # sinkID=ackL2Addr
                                                            (int(currSentPkt[4])     <= int(ack[4]))):            # sntASN<=ackASN
                    oneHopToSinkFound = True
                    if int(currSentPkt[16], 16) == int(currSentPkt[2], 16):      # L3Src==addr
                        for p in checkDelay:
                            if '#' not in p:
                                tmpLine = p.split()
                                if int(tmpLine[0]) == int(currSentPkt[16], 16) and int(tmpLine[1]) == int(currSentPkt[22]):
                                    insertedBefore = True
                                    break
                        printedOut = True
                        if not insertedBefore:
                            currentDelay = (int(ack[4]) - int(currSentPkt[4]) + 1) * MSPERSLOT
                            eachNodesPktDelay[int(currSentPkt[16], 16)-1].append(currentDelay)
                            checkDelay.append(" {:<7}{:<6}{:<14}{:<10}{:<12}{:<15}\n".format(int(currSentPkt[16], 16),  # source Addr
                                                                                        currSentPkt[22],              # packet ID
                                                                                        currSentPkt[14],              # number of Tx attempts
                                                                                        currSentPkt[4],               # sender's ASN
                                                                                        ack[4],                       # receiver's ASN
                                                                                        currentDelay                  # calculated Delay
                                                                                    ))
                            sentReceived_File.write(" {:<7}{:<6}{:<14}{:<10}{:<12}{:<15}\n".format(int(currSentPkt[16], 16),  # source Addr
                                                                                                currSentPkt[22],              # packet ID
                                                                                                currSentPkt[14],              # number of Tx attempts
                                                                                                currSentPkt[4],               # sender's ASN
                                                                                                ack[4],                       # receiver's ASN
                                                                                                currentDelay                  # calculated Delay
                                                                                            ))
                    else:
                        j = i-1
                        while j >= 0:
                            prevPkt = statFile[j].split()
                            if (prevPkt[0] == 'STAT_PK_TX' and prevPkt[20] == 'IANA_UDP' and 
                                                                (int(currSentPkt[16],16)  == int(prevPkt[16],16)) and   # currSntL3Src==prevSntL3Src
                                                                (int(currSentPkt[18],16) == int(prevPkt[18],16)) and   # currSntL3Dest==prevSntL3Dest
                                                                (int(currSentPkt[22]) == int(prevPkt[22])) and   # currSntSeqNum==prevSntSeqNum
                                                                (int(currSentPkt[4])  >  int(prevPkt[4]))):      # currSntASN>prevSntASN  
                                currSentPkt = prevPkt
                            j -= 1
                i += 1
            if not printedOut and 'STAT_PK_TX' in currSentPkt:
                for p in checkDelay:
                    if '#' not in p:
                        tmpLine = p.split()
                        if int(tmpLine[0]) == int(currSentPkt[16], 16) and int(tmpLine[1]) == int(currSentPkt[22]):
                            insertedBefore = True
                            break

                if not insertedBefore:
                    currentDelay = (int(ack[4]) - int(currSentPkt[4]) + 1) * MSPERSLOT
                    eachNodesPktDelay[int(currSentPkt[16], 16)-1].append(currentDelay)
                    checkDelay.append(" {:<7}{:<6}{:<14}{:<10}{:<12}{:<15}\n".format(int(currSentPkt[16], 16),  # source Addr
                                                                                        currSentPkt[22],              # packet ID
                                                                                        currSentPkt[14],              # number of Tx attempts
                                                                                        currSentPkt[4],               # sender's ASN
                                                                                        ack[4],                       # receiver's ASN
                                                                                        currentDelay                  # calculated Delay
                                                                                    ))
                    sentReceived_File.write(" {:<7}{:<6}{:<14}{:<10}{:<12}{:<15}\n".format(int(currSentPkt[16], 16),  # source Addr
                                                                                        currSentPkt[22],              # packet ID
                                                                                        currSentPkt[14],              # number of Tx attempts
                                                                                        currSentPkt[4],               # sender's ASN
                                                                                        ack[4],                       # receiver's ASN
                                                                                        currentDelay                  # calculated Delay
                                                                                    ))

    sentReceived_File.close()

    
    # *** per mote hop count to the sink
    maxHopDistance = 0
    for i in range(len(pathToSink)):
        if len(pathToSink[i]) == 0 and i+1 != sinkID:
            pathToSink[i] = findPath(destPath, i+1)

    for i in range(len(pathToSink)):
        # -1 : because path contains sink too
        if len(pathToSink[i])-1 > maxHopDistance:
            maxHopDistance = len(pathToSink[i])-1

    # remove secondary parent if exist
    for i in range(topologySize):
        tmpHopDist = []
        if pathToSink:
            for j in range(len(pathToSink[i])):
                tmpHopDist.append(str(len(pathToSink[int(pathToSink[i][j])-1])-1))
            repeated = set([x for x in tmpHopDist if tmpHopDist.count(x)>1])
            for ind, p in enumerate(repeated):
                tmpHopDist.pop(tmpHopDist.index(p))
                pathToSink[i].pop(tmpHopDist.index(p))


    # per node hop count
    hopDistance = [[] for i in range(maxHopDistance)]
    for i in range(topologySize):
        pathToSink[i]=list(set(pathToSink[i]))

        if len(pathToSink[i])-2 >= 0:
            hopDistance[len(pathToSink[i])-2].append(i+1)


    # *** store number of sent and received packets for a mote
    # rows: moteID ;        column0: num of sent packets, column1: num of received packets
    numOfSentAndReceivdPackets = [[0 for i in range(2)] for j in range(topologySize)]
    infile              = open('{0}finalStatSorted_asn.txt'.format(destPath), 'r')
    pktCounterTxHandler = infile.readlines()
    infile.close()

    infile              = open('{0}pkts_snt_rcvd_time.txt'.format(destPath), 'r')
    pktCounterRxHandler = infile.readlines()
    infile.close()

    # packet ID's starts from 0
    for line in pktCounterTxHandler:
        y = line.split()
        if y[0] == 'STAT_PK_TX' and y[20] == 'IANA_UDP':
            if numOfSentAndReceivdPackets[int(y[16],16) - 1][0] <= int(y[22]):
                numOfSentAndReceivdPackets[int(y[16],16) - 1][0] = int(y[22]) + 1

    minimumASN = 1000000
    maximumASN = 0
    for line in pktCounterRxHandler:
        if '#' not in line:
            y = line.split()
            numOfSentAndReceivdPackets[int(y[0]) - 1][1] += 1      
            # find start asn of generating data packets
            if minimumASN > int(y[3]):
                minimumASN = int(y[3])
            # find the asn of last received packet
            if maximumASN < int(y[4]):
                maximumASN = int(y[4])

    # pktSize(bit)/total time
    pktSize_to_totalTime = float(pktLength) / ((maximumASN-minimumASN)*0.015)

    maxNumSentPkts = 0
    for i in range(topologySize):
        if maxNumSentPkts < numOfSentAndReceivdPackets[i][0]:
            maxNumSentPkts = numOfSentAndReceivdPackets[i][0]

    # flow based delay & pdr
    delayPdrHandler = open('{0}delay_pdr.txt'.format(destPath), 'w')
    delayPdrHandler.write("#Source NumSentPkts NumReceivedPkts PDR    Throughput TotalTime MinDelay MaxDelay AvgDelay LowerBound UpperBound HopDistance AvgJitter\n")
    for moteID in range(topologySize):
        if moteID + 1 != sinkID:
            hopCount = 0
            for i in range(len(hopDistance)):
                for j in range(len(hopDistance[i])):
                    if int(hopDistance[i][j]) == moteID+1:
                        hopCount = i+1

            PDR = float(numOfSentAndReceivdPackets[moteID][1]) / numOfSentAndReceivdPackets[moteID][0]
            throughput = numOfSentAndReceivdPackets[moteID][1] * pktSize_to_totalTime
            avgDelay, lowerBound, upperBound = mean_confidence_interval(eachNodesPktDelay[moteID])
            if math.isnan(lowerBound):
                lowerBound = 0
            if math.isnan(upperBound):
                upperBound = 0
            delayPdrHandler.write(" {:<7}{:<12}{:<16}{:<7.3f}{:<11.3f}{:<11}{:<9}{:<9}{:<9.2f}{:<11.2f}{:<11.2f}{:<12}{:<9.2f}\n".format(
                                                                                               moteID + 1,                                      # mote ID
                                                                                               numOfSentAndReceivdPackets[moteID][0],           # number of sent packets
                                                                                               numOfSentAndReceivdPackets[moteID][1],           # number of received packets
                                                                                               PDR,                                             # PDR: Packet Delivery Ratio
                                                                                               throughput,                                      # throuput     
                                                                                               sum(eachNodesPktDelay[moteID]),                  # total delay of all packets
                                                                                               min(eachNodesPktDelay[moteID]),                  # minimum delay
                                                                                               max(eachNodesPktDelay[moteID]),                  # maximum delay
                                                                                               avgDelay,                                        # average delay
                                                                                               lowerBound,                                      # lower bound confidence interval
                                                                                               upperBound,                                      # higher bound confidence interval
                                                                                               hopCount,                                        # hop distance to the sink
                                                                                               calculateJitter(eachNodesPktDelay[moteID], avgDelay)  # calculate jitter of each flow
                                                                                               ))     
    delayPdrHandler.close()


    #*** x-coordinate: time, y-coordinate: PDR

    infile       = open('{0}pkts_snt_rcvd_time.txt'.format(destPath), 'r')
    delayHandler = infile.readlines()
    infile.close()

    outfile    = open('{0}timeBasedPDR.txt'.format(destPath), 'w')

    minASN = 1000000
    maxASN = 0
    for line in delayHandler:
        if '#' not in line:
            splittedLine = line.split()
            if int(splittedLine[3]) < minASN:
                minASN = int(splittedLine[3])
            if int(splittedLine[4]) > maxASN:
                maxASN = int(splittedLine[4])

    # decrement 6 minimal cells at the beginning of the slot frame
    minASN -= 6
    # is 4 slot frames so 4 packets
    intervals         = 4
    period            = intervals*101
    numSlottedPeriods = (maxASN - minASN) / period
    upperBoundAsn     = minASN + period

    outfile.write("#FlowID")
    for i in range(1, int(numSlottedPeriods)+1):
        if i < 10:
            outfile.write(" 0{0}  ".format(i))
        else:
            outfile.write(" {0}  ".format(i))

                        # skip sink
    for moteID in range(2, topologySize+1):
        outfile.write("\n {:<6}".format(moteID))
        pktCounter    = 0
        upperBoundAsn = minASN + period
        lowerBoundAsn = minASN
        while upperBoundAsn <= maxASN:
            for line in delayHandler:
                if '#' not in line:
                    splittedLine = line.split()
                    if int(splittedLine[3]) < upperBoundAsn and int(splittedLine[3]) >= lowerBoundAsn:
                        if int(splittedLine[0]) == moteID:
                            pktCounter += 1
            outfile.write(" {:<4.2}".format(float(pktCounter)/intervals))
            lowerBoundAsn  = upperBoundAsn
            upperBoundAsn += period
            pktCounter = 0
            '''
            if int(splittedLine[0]) == moteID:
                pktCounter = 1
            else:
                pktCounter = 0
            '''
    outfile.close()



if __name__ == "__main__":
    main(logPath, destPath, MSPERSLOT, numMinimalCells)

