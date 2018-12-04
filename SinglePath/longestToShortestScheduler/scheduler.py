import os
import Dodag
import xlsxwriter

if __name__ == "__main__":

    slotFrameLength = 101
    workbook  = xlsxwriter.Workbook('singlePath_scheduling.xlsx')
    dodagList = [filename for filename in os.listdir('.') if filename.startswith("dodag")]
    dodagList.sort()
    worksheet = ['' for i in range(len(dodagList))]
    for index, item in enumerate(dodagList):
        newDodag = Dodag.Dodag()

        # Read dodag from file
        newDodag.readDodag(item)

        # calculate hop distance of each node to the sink
        newDodag.setHopDistanceOfNodes()

        # calculate flow based sequential schedule
        newDodag.flowBasedSequentialScheduling(slotFrameLength)

        # write to file
        newDodag.writeScheduling("schedule_topology{0}".format(item[item.find('_'):]), 'startOfFlow_topology{0}'.format(item[item.find('_'):]))

        sheetName = "schedule_topology{0}".format(item[item.find('_'):item.find('.')])
        worksheet[index] = workbook.add_worksheet(sheetName)

        newDodag.exportScheduling(workbook, worksheet[index])

    workbook.close()
