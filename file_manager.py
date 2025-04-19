class AlgorithmData:
    def __init__(self):
        """
        realWeight : 실제 무게
        realLocation : 실제 적재 위치
        estimationWeight : 알고리즘이 추정하는 무게
        estimationLocation : 알고리즘이 추정하는 적재 위치
        errorValue : 오차값
        """
        self.timestamp = None
        self.realWeight = None
        self.realLocation = None
        self.estimationWeight = None
        self.estimationLocation = None
        self.errorValue = None

class FileManager:
    def __init__(self):
        self.file = None

    def loadDataFile(self, filePath):
        self.file = filePath
