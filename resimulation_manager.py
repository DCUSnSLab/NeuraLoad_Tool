from PyQt5.QtCore import QThread, pyqtSignal

from datainfo import SensorBinaryFileHandler, SensorFrame
from procsManager import ProcsManager
import multiprocessing as mp

class ResimulThread(QThread):
    finishSignal = pyqtSignal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        self.manager._start()
        self.finishSignal.emit()

class ResimulationManager(ProcsManager):
    def __init__(self, sm):
        super().__init__(sm)
        self.sm = sm
        self.procs = dict()
        self.file = None
        self.resbuffer = None
        self.algo_buffers = []

    def startThread(self, callback=None):  # callback은 스레드가 작업을 끝내고 실행하는 함수(버튼 활성화)
        self.thread = ResimulThread(self)
        if callback:
            self.thread.finishSignal.connect(callback)
        self.thread.start()

    def _start(self):
        for n, val in self.procs.items():
            readySig = mp.Event()
            databufQue = mp.Queue()

            val.event_readyBuffer(readySig, databufQue)

            p = mp.Process(name=n, target=val.run)
            val.start(p)

            readySig.wait()  # 큐 준비 완료 신호를 보낼때 까지 기다림
            self.addDataQue(databufQue.get())  # 데이터 큐
            self.resbuf[val.name] = databufQue.get()  # 결과 큐
            self.sendSensorData()

    def terminate(self):
        for val in self.procs.values():
            print(val,"terminated")
            self._print(val.name, val.getPID())
            val.terminate()
        self.procs.clear()
        self.removeDataQue()

    def getDataFile(self, filepath):
        self.file = filepath

    def addDataQue(self, dataque):
        if dataque not in self.algo_buffers:
            self.algo_buffers.append(dataque)

    def removeDataQue(self):
        self.algo_buffers.clear()

    def sendSensorData(self):
        """
        bin파일에 있는 데이터를 읽어와 알고리즘 버퍼에 전달
        """
        records = self.load_File()
        for data in records:
            for algo_buf in self.algo_buffers:
                algo_buf.put(data)

        for algo_buf in self.algo_buffers:
            algo_buf.put(SensorFrame(timestamp=None, sensors=None, isEoF=True))

    def load_File(self):
        loadData = SensorBinaryFileHandler(self.file).load_frames()
        return loadData
