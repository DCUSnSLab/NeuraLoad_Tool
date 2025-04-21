import os
from enum import Enum

from datainfo import SensorData, SENSORLOCATION
import struct
import datetime
import time

class AlgorithmDataInfo:
    def __init__(self):
        """
        realWeight : 실제 무게
        realLocation : 실제 적재 위치
        estimationWeight : 알고리즘이 추정하는 무게
        estimationLocation : 알고리즘이 추정하는 적재 위치
        errorValue : 오차값
        """
        self.timestamp = None
        self.realWeight = None
        self.realLocation = None
        self.estimationWeight = None
        self.estimationLocation = None
        self.errorValue = None

class SensorLocation(Enum):
    TopLeft = 0
    BottomLeft = 1
    TopRight = 2
    BottomRight = 3
    NONE = -1

    @staticmethod
    def from_string(name: str) -> 'SensorLocation':
        name = name.strip().replace(" ", "").lower()
        mapping = {
            "topleft": SensorLocation.TopLeft,
            "bottomleft": SensorLocation.BottomLeft,
            "topright": SensorLocation.TopRight,
            "bottomright": SensorLocation.BottomRight
        }
        return mapping.get(name, SensorLocation.NONE)

class FileManager:
    def __init__(self):
        self.file = None
        self.dataque = None
        self.resbuffer = None

    def loadDataFile(self, filepath):
        self.file = filepath

    def addDataQue(self, dataque):
        self.dataque = dataque

    def removeDataQue(self, dataque):
        if dataque in self.dataque:
            self.dataque.remove(dataque)

    def sendSensorData(self):
        """
        bin파일에 있는 데이터를 알고리즘 버퍼에 전달
        """
        records = self.readBinFile()
        recordsGroup = self.groupSensorData(records)
        for data in recordsGroup:
            self.dataque.put(data)
        print("Clear")

        self.dataque.put("__DONE__")

    def readBinFile(self):
        records = []

        with open(self.file, 'rb') as f:
            while True:
                block = f.read(52)
                if len(block) < 52:
                    break

                timestamp_int = struct.unpack('<I', block[0:4])[0]
                timestamp_str = str(timestamp_int).zfill(9)
                timestamp = datetime.datetime.strptime(timestamp_str, '%H%M%S%f')

                name = block[23:39].decode('utf-8').rstrip('\x00')
                value1, value2, value3 = struct.unpack('<fff', block[39:51])

                location_enum = self._get_SensorLocation(name)

                sensor  = SensorData(
                    serialport=name,
                    timestamp=timestamp,
                    loc=location_enum.value,  # 실제 센서 위치 파악 가능하다면 설정
                    value=int(value1),
                    sub_part1=int(value2),
                    sub_part2=int(value3)
                )
                records.append(sensor)

        return records

    def _get_SensorLocation(self, name: str):
        name = name.strip()
        slocNum = SensorLocation.from_string(name)
        return slocNum

    def groupSensorData(self, records, threshold=0.1):
        # records.sort(key=lambda x: x.timestamp)
        groupData = []
        buffer = []

        # for data in records:
        #     if not buffer:
        #         buffer.append(data)
        #     else:
        #         delta = (data.timestamp - buffer[0].timestamp).total_seconds()
        #         if delta <= threshold:
        #             buffer.append(data)
        #         else:
        #             if len(buffer) == 4:
        #                 groupData.append(buffer.copy())
        #             buffer = [data]
        for data in records:
            if not buffer:
                buffer.append(data)
            else:
                buffer.append(data)
                if len(buffer) == 4:
                    groupData.append(buffer.copy())
                    buffer.clear()
        if len(buffer) == 4:
            groupData.append(buffer.copy())

        return groupData

class AlgorithmFileManager():
    def __init__(self):
        self.files = dict()

    def loadAlgorithmFromFile(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]
        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files[file_name] = full_path
        return self.files