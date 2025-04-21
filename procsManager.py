from PyQt5.QtCore import QThread, pyqtSignal

from Algorithm.COGMassEstimation_v2 import COGMassEstimation
from Algorithm.MLPPredictor import KerasMLPPredictor
from Algorithm.RandomForestPredictor import RandomForestPredictor
import multiprocessing as mp

class ProcsManagerThread(QThread):
    finishSignal = pyqtSignal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        self.manager._start()
        self.finishSignal.emit()

class ProcManagerResimulThread(QThread):
    finishSignal = pyqtSignal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        self.manager._startResimulation()
        self.finishSignal.emit()

class ProcsManager:
    def __init__(self, manager):
        self.procs = dict()
        self.manager = manager
        self.resbuf = dict()
        self.thread = None

    def addProcess(self, algoName):
        if algoName == "COGMassEstimation_v2.py":
            algo = COGMassEstimation(algoName)
        elif algoName == "MLPPredictor.py":
            algo = KerasMLPPredictor(algoName)
        elif algoName == "RandomForestPredictor.py":
            algo = RandomForestPredictor(algoName)
        else:
            return

        self.procs[algoName] = algo

    def startThread(self, ResimulMode=False, callback=None):  # callback은 스레드가 작업을 끝내고 실행하는 함수(버튼 활성화)
        if ResimulMode:
            self.thread = ProcManagerResimulThread(self)
        else:
            self.thread = ProcsManagerThread(self)
        if callback:
            self.thread.finishSignal.connect(callback)
        self.thread.start()

    def _start(self):  # 스레드로 실행 (기존 start)
        for n, val in self.procs.items():
            readySig = mp.Event()
            databufQue = mp.Queue()

            val.event_readyBuffer(readySig, databufQue)

            p = mp.Process(name=n, target=val.run)
            val.start(p)

            readySig.wait()  # 큐 준비 완료 신호를 보낼때 까지 기다림
            self.manager.add_buffer(databufQue.get())  # 데이터 큐
            self.resbuf[val.name] = databufQue.get()  # 결과 큐

    def _startResimulation(self):
        for n, val in self.procs.items():
            readySig = mp.Event()
            databufQue = mp.Queue()

            val.event_readyBuffer(readySig, databufQue)

            p = mp.Process(name=n, target=val.runResimul)
            val.start(p)

            readySig.wait()  # 큐 준비 완료 신호를 보낼때 까지 기다림
            self.manager.addDataQue(databufQue.get())  # 데이터 큐
            self.resbuf[val.name] = databufQue.get()  # 결과 큐
            self.manager.sendSensorData()

    def getResultBufs(self):
        return self.resbuf

    def terminate(self):
        for val in self.procs.values():
            print(val,"terminated")
            self.__print(val.name, val.getPID())
            val.terminate()
        self.procs.clear()
        self.manager.remove_buffer(self.resbuf)

    def terminateResimulation(self):
        for val in self.procs.values():
            print(val,"terminated")
            self.__print(val.name, val.getPID())
            val.terminate()
        self.procs.clear()
        # self.manager.removeDataQue(self.resbuf)

    def join(self):
        pass

    def __print(self, name, pid):
        print('[%d] - %s'%(pid, name))

