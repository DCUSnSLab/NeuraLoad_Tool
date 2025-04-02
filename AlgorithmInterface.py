from abc import *

class AlgorithmInterface():
    def __init__(self):
        '''
        self.name: 알고리즘 파일 이름
        self.input: 들어오는 센서값
        self.model: 알고리즘 모델 경로
        self.weights: 현재 무게
        self.position: 현재 무게의 위치
        '''

        self.name = None
        self.input = None
        self.model = None
        self.weights = None
        self.position = None

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def getdata(self):
        '''
        추정 무게 값 리턴(float)
        추정 무게 위치 값 리턴(int)
        '''
        pass