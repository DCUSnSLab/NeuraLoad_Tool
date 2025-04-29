from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SensorBinaryFileHandler, SensorFrame, AlgorithmFileHandler, AlgorithmData
from procsManager import ProcsManager
import multiprocessing as mp

class ResimulThread(QThread):
    finishSignal = pyqtSignal()
    datacallback = pyqtSignal(int, SensorFrame, AlgorithmData)
    resimcompleteCallback = pyqtSignal(list)
    statuscallback = pyqtSignal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.manager.on_DataProcessed(self.on_dataCallback)
        self.manager.on_Status(self.on_statuscallback)
        self.manager.on_ResimComp(self.on_ResimCompleteCallback)


    def on_dataCallback(self, i, sf:SensorFrame, legacy_ad:AlgorithmData = None):
        self.datacallback.emit(i, sf, legacy_ad)

    def on_statuscallback(self, str):
        self.statuscallback.emit(str)

    def on_ResimCompleteCallback(self, data):
        self.resimcompleteCallback.emit(data)

    def run(self):
        self.manager._start()
        self.finishSignal.emit()

class ResimulationManager(ProcsManager):
    def __init__(self, sm):
        super().__init__(sm)
        self.sm = sm
        self.procs = dict()
        self.file = None
        self.algo_buffers = dict()
        self.filehandler: dict = {}
        self.DataEventHandler = []
        self.statusHandler = []
        self.ResimCompHandler = []

    def startThread(self, callback=None, datacallback=None, statuscallback=None, resimcompcallback=None):  # callback은 스레드가 작업을 끝내고 실행하는 함수(버튼 활성화)
        self.thread = ResimulThread(self)
        if callback:
            self.thread.finishSignal.connect(callback)
            self.thread.datacallback.connect(datacallback)
            self.thread.statuscallback.connect(statuscallback)
            self.thread.resimcompleteCallback.connect(resimcompcallback)
        self.thread.on_statuscallback('Start Resimulation..')
        self.thread.start()

    def _start(self):
        for n, val in self.procs.items():
            self.thread.on_statuscallback(f'Load Process {n} ...')
            readySig = mp.Event()
            databufQue = mp.Queue()

            val.event_readyBuffer(readySig, databufQue)

            p = mp.Process(name=n, target=val.run)
            val.start(p)
            self.thread.on_statuscallback(f'Start Process {n} ...')

            readySig.wait()  # 큐 준비 완료 신호를 보낼때 까지 기다림
            dataque = databufQue.get()
            self.addDataBuffer(val.name, dataque)  # 데이터 큐
            self.addResBuffer(val.name, databufQue.get())  # 결과 큐
            self.setFileHandler(val.name)

            self.thread.on_statuscallback(f'{n}: Send Sensor Data to Algorithm...')
            datasize = self.sendSensorData()
            self.thread.on_statuscallback(f'{n}: Save Algorithm Data {self.filehandler[val.name]} ...')
            self.saveDatainFile(datasize)
            self.terminate(val)

    def finishResimulProc(self, name):
        self.terminate(name)
        self.removeDataBuffer(name)

    def terminateAll(self):
        for val in self.procs.values():
            self._print(val.name, val.getPID())
            val.terminate()
        self.procs.clear()
        self.algo_buffers.clear()
        self.resbuf.clear()

    def setDataFile(self, filepath):
        self.file = filepath

    def load_File(self):
        loadData = SensorBinaryFileHandler(self.file).load_frames()
        return loadData

    def setFileHandler(self, name):
        filename = Path(self.file).name.split('_')
        filename = '_'.join(filename[1:])
        refilename = f"re_{name}_{filename}"
        self.filehandler[name] = refilename

    def sendSensorData(self):
        """
        bin파일에 있는 데이터를 읽어와 알고리즘 버퍼에 전달
        """
        records = self.load_File()
        for data in records:
            for name, algo_buf in self.algo_buffers.items():
                algo_buf.put(data)

        for name, algo_buf in self.algo_buffers.items():
            algo_buf.put(SensorFrame(timestamp=None, sensors=None, isEoF=True))

        return len(records)

    def saveDatainFile(self, datasize):
        for algo_name, val in self.resbuf.items():
            if not val.empty():
                datas = self.refBuftoList(val, algo_name, datasize)
                self._ResimComplete(datas)
                filename = self.filehandler[algo_name]
                SensorBinaryFileHandler(filename).save_frames(datas)
        print("End")


    def refBuftoList(self, val, algo_name, datasize):
        val_list = []
        i = 1
        while True:
            data =val.get()
            sf:SensorFrame = data['input']
            ad:AlgorithmData = data['output']
            legacy_ad = sf.algorithms
            if sf.isEoF:
                break
            ad.algo_type = ALGORITHM_TYPE.from_name(algo_name)
            sf.algorithms = ad
            val_list.append(sf)

            #cal percentage
            per = i/datasize*100
            self._DataProcessed(int(per), sf, legacy_ad)
            i+=1
        return val_list

    def on_ResimComp(self, handle):
        self.ResimCompHandler.append(handle)

    def _ResimComplete(self, data):
        for handler in self.ResimCompHandler:
            handler(data)

    def on_DataProcessed(self, handle):
        self.DataEventHandler.append(handle)

    def _DataProcessed(self, i, sf:SensorFrame, legacy_ad:AlgorithmData = None):
        for handler in self.DataEventHandler:
            handler(i, sf, legacy_ad)

    def on_Status(self, handle):
        self.statusHandler.append(handle)

    def _StatusChanged(self, str):
        for handler in self.DataEventHandler:
            handler(str)