#!/usr/bin/env python
import operator
import os
import random
import argparse
import json
from math import radians, cos, sin, asin, sqrt, log10


parser = argparse.ArgumentParser()
parser.add_argument('--repeat',
                    dest='repeat',
                    type=int,
                    default=1,
                    help='Frequency of each topology size.',
                    )
parser.add_argument('--firstSize',
                    dest='firstSize',
                    type=int,
                    default=8,
                    help='first topology size.',
                    )
parser.add_argument('--lastSize',
                    dest='lastSize',
                    type=int,
                    default=10,
                    help='last topology size.',
                    )
parser.add_argument('--step',
                    dest='topoIncStep',
                    type=int,
                    default=1,
                    help='steps of increasing topology size.',
                    )
parser.add_argument('--pdrThresh',
                    dest='pdrThreshold',
                    type=float,
                    default=0.01,
                    help='links less than this PDR will be deleted.',
                    )
parser.add_argument('--seed',
                    dest='seedTopology',
                    type=int,
                    default=1,
                    help='be able to regenerate same topology',
                    )
parser.add_argument('--pathResultDir',
                    dest='pathResults',
                    type=str,
                    default='generatedTopologies',
                    help='determine path to store results',
                    )
parser.add_argument('--root',
                    dest='DAGroot',
                    type=int,
                    default=1,
                    help='set dag root',
                    )

parameters = parser.parse_args()
parameters = parameters.__dict__

FREQUENCY_GHz    = 2.4
TX_POWER_dBm     = 0.0
PISTER_HACK_LOSS = 40.0
SENSITIVITY_dBm  = -101.0
GREY_AREA_dB     = 15.0

# number of repetition for each topology size
for repeat in range(1, parameters['repeat'] + 1):
    random.seed(repeat)
    # topology sizes with increasing step
    for topologySize in range(parameters['firstSize'], parameters['lastSize'] + 1, parameters['topoIncStep']):
        output = ''
        output += "{\"connections\": ["
        moteList = []
        # creating links for given topology size
        for i in range(1, topologySize+1):
            moteList.append(i)
            # Creates a fully-meshed, but do not create those with pdr lower than threshold
            for j in moteList[:-1]:
                pdr = random.random()
                if pdr > parameters['pdrThreshold']:
                    output += "{\"fromMote\": "
                    output += str(i)
                    output += ", \"toMote\": "
                    output += str(j)
                    output += ", \"pdr\": "
                    output += str(pdr)
                    output += "}, "

        # deleting ', ' from end of string
        output = output[:-2]
        # Initialize DAGroot
        output += '], \"DAGrootList\": [{0}], \"motes\": ['.format(parameters['DAGroot'])

        # X and Y coordinates of all motes in one topology
        for i in range(1, topologySize+1):
            output += "{\"lat\": "
            output += str(37.875095 - 0.0008 + random.random() * 0.0004 * sqrt(topologySize))
            output += ", \"lon\": "
            output += str(-122.257473 - 0.0008 + random.random() * 0.0004 * sqrt(topologySize))
            output += ", \"id\": "
            output += str(i)
            output += "}, "

            # deleting ', ' from end of string
        output = output[:-2]
        output += ']}'

        path = ""
        path += parameters['pathResults']                                 # seed
        path += "/topology_{0}_{1}_{2}.json".format(topologySize, repeat, repeat)  # parameters['seedTopology'])
        # path = ../results/generatedTopologies/topology_size_repeat_seed.json
        f = open(path, 'w')
        f.write(output)
        f.close()

        # *** apply constraints
        random.seed(repeat + 2)
        # set number of nodes for each level of DODAG
        numNodesPerHopDist = []
        # except sink
        remainedNodes = 1
        while remainedNodes != topologySize:
            if topologySize - remainedNodes > 2:
                if topologySize - remainedNodes > 5:
                    numNodesPerHopDist.append(random.randint(3, 5))
                else:
                    numNodesPerHopDist.append(random.randint(3, topologySize - remainedNodes))
                remainedNodes += numNodesPerHopDist[-1]
            elif topologySize - remainedNodes > 0:
                numNodesPerHopDist.append(topologySize - remainedNodes)
                remainedNodes += numNodesPerHopDist[-1]

        # load topology
        topoConfig = open(path)
        topo = json.load(topoConfig)
        connect = topo['connections']
        motes = topo['motes']
        # compute distance
        listZeroPDR = []
        for i in range(topologySize-1):
            j = i + 1
            while j < topologySize:
                lonFrom = [(lon['lon']) for lon in motes if lon['id'] == i + 1]
                latFrom = [(lat['lon']) for lat in motes if lat['id'] == i + 1]
                lonTo = [(lon['lon']) for lon in motes if lon['id'] == j + 1]
                latTo = [(lat['lon']) for lat in motes if lat['id'] == j + 1]
                lonFrom, latFrom, lonTo, latTo = map(radians, [lonFrom[0], latFrom[0], lonTo[0], latTo[0]])
                dlon = lonTo - lonFrom
                dlat = latTo - latFrom
                a = sin(dlat / 2) ** 2 + cos(latFrom) * cos(latTo) * sin(dlon / 2) ** 2
                c = 2 * asin(sqrt(a))
                d_km = 6367 * c
                # compute reception power (first Friis, then apply Pister-hack)
                Prx = TX_POWER_dBm - (20 * log10(d_km) + 20 * log10(FREQUENCY_GHz) + 92.45)
                Prx -= PISTER_HACK_LOSS * random.random()

                # turn into PDR
                if Prx < SENSITIVITY_dBm:
                    pdr = 0.0
                elif Prx > SENSITIVITY_dBm + GREY_AREA_dB:
                    pdr = 1.0
                else:
                    pdr = (Prx - SENSITIVITY_dBm) / GREY_AREA_dB

                for index, co in enumerate(connect):
                    if (int(co['fromMote']) == i+1 and int(co['toMote']) == j+1) or (int(co['fromMote']) == j+1 and int(co['toMote']) == i+1):
                        co['pdr'] = pdr
                        if pdr == 0:
                            listZeroPDR.append(index)
                        break
                j += 1

        # sort links based on their PDR: descending order
        for first in range(len(connect)-1):
            for second in range(first+1, len(connect)):
                if connect[first]['pdr'] < connect[second]['pdr']:
                    tmp = connect[second]
                    connect[second] = connect[first]
                    connect[first] = tmp

        # list of neighbors per mote: row: moteID, col: neighbors
        moteConnections = [[] for j in range(topologySize)]
        for i in range(topologySize):
            for co in connect:
                fromMote = int(co['fromMote'])
                toMote = int(co['toMote'])
                if i + 1 == fromMote:
                    moteConnections[i].append(toMote)
                elif i + 1 == toMote:
                    moteConnections[i].append(fromMote)

        # first node is sink, remove all sink IDs in connections matrix
        itemsSelected = [parameters['DAGroot']]
        for i in range(len(moteConnections)):
            j = 0
            while j < len(moteConnections[i]):
                if moteConnections[i][j] in itemsSelected:
                    moteConnections[i].pop(j)
                    j -= 1
                j += 1

        currentLevel = [itemsSelected[-1]]
        # keeps final connections
        # children[][]:: row: parent ID, column: children ID
        children = [[] for i in range(topologySize)]
        # in each level of DODAG traverse through the connections and find a connection which one side of it is in currentLevel
        # and the other side is not in itemsSelected. A selected connection is added to children array
        while numNodesPerHopDist:
            numConnections = numNodesPerHopDist.pop(0)
            index = 0
            for co in connect:
                fromMote = int(co['fromMote'])
                toMote = int(co['toMote'])
                if index < numConnections:
                    if fromMote in currentLevel:
                        if toMote not in itemsSelected:
                            itemsSelected.append(toMote)
                            children[fromMote-1].append(toMote)
                            index += 1
                    elif toMote in currentLevel:
                        if fromMote not in itemsSelected:
                            itemsSelected.append(fromMote)
                            children[toMote-1].append(fromMote)
                            index += 1
                else:
                    break
            # current level is now the next level. nodes chosen as next level
            currentLevel = itemsSelected[-numConnections:] if numConnections > 1 else [itemsSelected[-1]]
            # delete selected items from connections maxrix
            for i in range(len(moteConnections)):
                j = 0
                while j < len(moteConnections[i]):
                    if moteConnections[i][j] in itemsSelected:
                        moteConnections[i].pop(j)
                        j -= 1
                    j += 1

        # setting second parent
        # condition: best parent and second parent must have same parent.
        # In other words single grand parent and same length of both path
        output = ''
        output += "{\"nodeStatus\": ["
        for i in itemsSelected:
            for j in range(len(children[i-1])):
                output += "{\"moteID\": "
                output += str(children[i-1][j])
                output += ", \"bestParent\": "
                output += str(i)
                output += ", \"secondParent\": "
                output += str(0) if i == parameters['DAGroot'] else '-1'
                output += ", \"grandParent\": "
                output += str(0) if i == parameters['DAGroot'] else '-1'
                output += "}, "
        # deleting ', ' from end of string
        output = output[:-2]
        # end of record
        output += ']}'

        f = open("tempTopo.json", 'w')
        f.write(output)
        f.close()

        # load topology
        temp = open("tempTopo.json")
        os.remove("tempTopo.json")
        tempTopo = json.load(temp)
        links = tempTopo['nodeStatus']

        # find grand parent of each node
        for first, co in enumerate(links):
            prefParent = co['moteID']
            second = first + 1
            while second < len(links):
                if links[second]['bestParent'] == prefParent:
                    links[second]['grandParent'] = co['bestParent']
                second += 1

        # find second parent
        # pair of nodes: select pair of nodes which do not have second parent and assign them together.
        for first, co in enumerate(links):
            if co['grandParent'] != 0:
                second = first + 1
                while second < len(links):
                    if (links[second]['grandParent'] == co['grandParent'] and
                            links[second]['secondParent'] == co['secondParent'] and
                            links[second]['bestParent'] != co['bestParent'] and
                            co['secondParent'] < 0):
                        links[second]['secondParent'] = co['bestParent']
                        co['secondParent'] = links[second]['bestParent']
                        break
                    second += 1
        # single nodes in each level: second parent of nodes are set to one best parent of same level nodes
        for first in links:
            if first['grandParent'] != 0 and first['secondParent'] == -1:
                for second in links:
                    if (second['bestParent'] == first['grandParent'] or second['secondParent'] == first['grandParent']) and second['moteID'] != first['bestParent']:
                        first['secondParent'] = second['moteID']
                        break

        # set PDR for each link: secondParent => pdr=0.6 & bestParent => pdr=1.0
        itemsToRemove = []
        for index, co in enumerate(connect):
            linkFound = False
            for li in links:
                if co['fromMote'] == li['moteID']:
                    if co['toMote'] == li['bestParent']:
                        linkFound = True
                        break
                    elif co['toMote'] == li['secondParent']:
                        linkFound = True
                        break
                elif co['toMote'] == li['moteID']:
                    if co['fromMote'] == li['bestParent']:
                        linkFound = True
                        break
                    elif co['fromMote'] == li['secondParent']:
                        linkFound = True
                        break
            if not linkFound:
                itemsToRemove.append(index)

        topo['connections'] = [x for i, x in enumerate(connect) if i not in itemsToRemove]
        f = open(path, 'w')
        topo = str(topo).replace("'", "\"")
        f.write(str(topo).replace("u", ""))
        f.close()


# statistics of created topologies
banner = ['']
banner += ['{0} topologies created.'.format(parameters['repeat'] * (((parameters['lastSize'] - parameters['firstSize']) / parameters['topoIncStep']) + 1))]
banner += ['Each topology size repeated {0} times. Repeat number is used for seed too.'.format(parameters['repeat'])]
banner += ['Starting from {0} nodes to {1} nodes with {2} nodes increasing step.'.format(parameters['firstSize'], parameters['lastSize'], parameters['topoIncStep'])]
banner += ['PDR threshold: {0}'.format(parameters['pdrThreshold'])]
banner = '\n'.join(banner)

print(banner)
print('')
