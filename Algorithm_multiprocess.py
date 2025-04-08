import copy
import os
import sys
import importlib.util
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque

from AlgorithmInterface import AlgorithmBase
from arduino_manager import SerialThread, get_arduino_ports
from experiment import Experiment
import multiprocessing
from multiprocessing import Process, Queue
import time

class Algorithm_multiprocess:
    def __init__(self, file_input):
        self.file_name_input = file_input

    def run(self, file_name_input):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        full_path = os.path.join(folder, file_name_input)

        file_name = os.path.splitext(os.path.basename(full_path))[0]
        spec = importlib.util.spec_from_file_location(file_name, full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, AlgorithmBase) and obj is not AlgorithmBase:
                instance = obj()
                while True:
                    result = instance.execute()
                    print('aaa => ', result)
                    # result_queue.put(str(result))