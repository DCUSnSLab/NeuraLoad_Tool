from Algorithm.COGMassEstimation import COGMassEstimation
from Algorithm.MLPPredictor import KerasMLPPredictor
from Algorithm.RandomForestPredictor import RandomForestPredictor
import multiprocessing as mp

class ProcsManager:
    def __init__(self, sm):
        self.procs = dict()
        self.sm = sm

    def addProcess(self, algoName):
        if algoName == "COGMassEstimation.py":
            algo = COGMassEstimation(algoName)
        elif algoName == "MLPPredictor.py":
            algo = KerasMLPPredictor()
        elif algoName == "RandomForestPredictor.py":
            algo = RandomForestPredictor()
        else:
            return

        self.procs[algoName] = algo

    def start(self):
        for n, val in self.procs.items():
            p = mp.Process(name=n, target=val.run)
            val.start(p)
            val.getSerialManager(self.sm)

        #프로세스가 시작됐는지(정확히는, databuf 가 만들어졌는지 확인 한 후에, SerialManager에 그 버퍼를 등록해 줘야 함

    def terminate(self):
        for val in self.procs.values():
            val.terminate()
            self.__print('%15s(%5d) has been terminated' % (val.name, val.getPID()))

    def join(self):
        pass

    def __print(self, data):
        print('[%d-%s] - %s'%(self.getPID(), self.name, data))

