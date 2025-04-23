import os
from enum import Enum

from datainfo import SensorData, SENSORLOCATION
import struct
import datetime
import time

class AlgorithmFileManager():
    """
    알고리즘 파일 목록을 반환
    실시간 알고리즘 테스트, 리시뮬레이션 모두 동일하게 사용해서 만들게 됨
    """
    def __init__(self):
        self.files = dict()

    def loadAlgorithmFromFile(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]
        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files[file_name] = full_path
        return self.files
