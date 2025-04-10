import multiprocessing as mp
import multiprocessing.context
import multiprocessing.managers
import os
from abc import *

class processImpl(metaclass=ABCMeta):
    def __init__(self,name):
        self.name = name
        self.process = None

    def _initialize_buffers(self):
        self.manage = mp.Manager()
        self.databuf = self.manage.Queue()
        self.databuf.put(self.name)
        print(self.databuf.get())

    def getSerialManager(self, sm):
        self.sm = sm
        self.sm.testprint()

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
        self.process.terminate()

    def run(self):
        self._initialize_buffers()
        self.doProc()
        # self.join()
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

    def getDatabuf(self):
        return self.databuf

    def _print(self, data):
        print('[%d-%s] - %s'%(self.getPID(), self.name, data))

    @abstractmethod
    def doProc(self):
        pass