import multiprocessing as mp
import multiprocessing.context
import multiprocessing.managers
import os
from abc import *

class processImpl(metaclass=ABCMeta):
    def __init__(self,name):
        self.name = name
        self.process = None
        self.readySig = None
        self.databuf = None
        self.manage = None
        self.resBuf = None
        self.terminate_event = mp.Event()  # 자식 프로세스 종료 이벤트

    def _initialize_buffers(self):
        self.manage = mp.Manager()
        self.databuf = self.manage.Queue()
        self.resBuf = self.manage.Queue()
        if self.readySig:
            self.readyQue.put(self.databuf)  # 센서데이터 큐
            self.readyQue.put(self.resBuf)  # 알고리즘 결과 큐
            self.readySig.set()  # 완료 신호

    def getDatabuf(self):
        return self.databuf

    def getResultBuf(self):
        return self.resBuf

    def event_readyBuffer(self, event, queue):
        self.readySig = event
        self.readyQue = queue  # PM한테 전송할 큐

    def start(self, proc:multiprocessing.context.Process):
        self.process = proc
        self.process.start()
        self._print('Process started')

    def is_alive(self):
        if self.process is None:
            return False
        else:
            return self.process.is_alive()

    def join(self):
        self.process.join()

    def terminate(self):
        self.terminate_event.set()  # 내부 루트에 종료 신호 전송
        self.join()  # 종료될 때까지 기다림
        if self.process and self.process.is_alive():
            self.process.terminate()
        else:
            print('No Process found')

    def run(self):
        self._initialize_buffers()
        self.doProc()
        self.__done()

    def __done(self):
        self._print('Finished Process')

    def getPID(self):
        if self.process is None:
            return os.getpid()
        else:
            return self.process.pid

    def _getDataQueue(self):
        return self.databuf.get()

    def _print(self, data):
        print('[%d-%s] - %s'%(self.getPID(), self.name, data))

    @abstractmethod
    def doProc(self):
        pass
