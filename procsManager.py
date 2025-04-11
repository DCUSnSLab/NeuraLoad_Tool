from Algorithm.COGMassEstimation import COGMassEstimation
from Algorithm.MLPPredictor import KerasMLPPredictor
from Algorithm.RandomForestPredictor import RandomForestPredictor
import multiprocessing as mp

class ProcsManager:
    def __init__(self, sm):
        self.procs = dict()
        self.sm = sm
        self.resbuf = dict()

    def addProcess(self, algoName):
        if algoName == "COGMassEstimation.py":
            algo = COGMassEstimation(algoName)
        elif algoName == "MLPPredictor.py":
            algo = KerasMLPPredictor(algoName)
        elif algoName == "RandomForestPredictor.py":
            algo = RandomForestPredictor(algoName)
        else:
            return

        self.procs[algoName] = algo

    def start(self):
        for n, val in self.procs.items():
            readySig = mp.Event()
            databufQue = mp.Queue()

            val.event_readyBuffer(readySig, databufQue)

            p = mp.Process(name=n, target=val.run)
            val.start(p)

            readySig.wait()  # 자식이 큐 준비 신호를 보낼때 까지 기다림
            self.sm.add_buffer(databufQue.get())
            self.resbuf[val.name] = databufQue.get()

    def getResultBufs(self):
        return self.resbuf

    def terminate(self):
        for val in self.procs.values():
            val.terminate()
            self.__print('%15s(%5d) has been terminated' % (val.name, val.getPID()))

    def join(self):
        pass

    def __print(self, name, pid):
        print('[%d] - %s'%(pid, name))

