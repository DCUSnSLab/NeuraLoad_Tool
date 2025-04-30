from PyQt5.QtCore import QThread, pyqtSignal

from Algorithm.COGMassEstimation_v2 import COGMassEstimation
from Algorithm.MLPPredictor import KerasMLPPredictor
from Algorithm.RandomForestPredictor import RandomForestPredictor
from Algorithm.COGPositionMassEstimation import COGPositionMassEstimation
import multiprocessing as mp

from Algorithm.algorithmtype import ALGORITHM_TYPE


class ProcsManagerThread(QThread):
    finishSignal = pyqtSignal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        self.manager._start()
        self.finishSignal.emit()

class ProcsManager:
    def __init__(self, sm):
        self.procs = dict()
        self.sm = sm
        self.resbuf = dict()
        self.thread = None
        self._ready_handlers = []
        self.algo_buffers = dict()

    def on_ready(self, handler):
        self._ready_handlers.append(handler)

    def _AlgorithmReady(self):
        for handler in self._ready_handlers:
            handler()

    def addProcess(self, algoName, resimMode=False):
        if algoName == ALGORITHM_TYPE.COGMassEstimation:
            algo = COGMassEstimation(algoName.name)
        elif algoName == ALGORITHM_TYPE.MLPPredictor:
            algo = KerasMLPPredictor(algoName.name)
        elif algoName == ALGORITHM_TYPE.RandomForestPredictor:
            algo = RandomForestPredictor(algoName.name)
        elif algoName == ALGORITHM_TYPE.COGPositionMassEstimation:
            algo = COGPositionMassEstimation(algoName.name)
        elif algoName == ALGORITHM_TYPE.COGPositionMassEstimation_v2:
            algo = COGPositionMassEstimation(algoName.name)
        else:
            return

        algo.setResimMode(resimMode)
        self.procs[algoName.name] = algo

    def startThread(self, callback=None):  # callback은 스레드가 작업을 끝내고 실행하는 함수(버튼 활성화)
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
            dataque = databufQue.get()
            self.addDataBuffer(val.name, dataque)
            self.sm.add_buffer(dataque)  # 데이터 큐
            self.addResBuffer(val.name, databufQue.get())  # 결과 큐

        self._AlgorithmReady()

    def addDataBuffer(self, name, dataque):
        if name not in self.algo_buffers:
            self.algo_buffers[name] = dataque

    def addResBuffer(self, name, dataque):
        if name not in self.resbuf:
            self.resbuf[name] = dataque

    def removeDataBuffer(self, name):
        if name in self.algo_buffers:
            del self.algo_buffers[name]

    def removeResBuffer(self, name):
        if name in self.resbuf:
            del self.resbuf[name]

    def removeSerialManagerBuffer(self, buf):
        self.sm.remove_buffer(buf)

    def getResultBufs(self):
        return self.resbuf

    def terminate(self, name):
        if name in self.procs:
            print(name, "terminated")
            self._print(name, self.procs[name].getPID())
            self.procs[name].terminate()
            del self.procs[name]
            if name in self.algo_buffers:
                self.removeDataBuffer(name)
            if name in self.resbuf:
                self.removeResBuffer(name)

    def terminateAll(self):
        for val in self.procs.values():
            self._print(val.name, val.getPID())
            val.terminate()
        for algo_buf in self.algo_buffers.values():
            self.removeSerialManagerBuffer(algo_buf)
        self.procs.clear()
        self.resbuf.clear()
        self.algo_buffers.clear()

    def join(self):
        pass

    def _print(self, name, pid):
        print('[%d] - %s'%(pid, name))
