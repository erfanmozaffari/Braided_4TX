

class DodagNode:
    def __init__(self, nodeId):
        self.sink = False
        self.Id = nodeId
        self.load = 0
        self.hopDistance = -1
        self.NumChild = 0
        self.parent = []
        self.secondParent = []
