import os
from dataclasses import dataclass
from enum import Enum
from typing import List, BinaryIO
import struct
import datetime
import threading
import time
from collections import deque
import csv
from Algorithm.algorithmtype import ALGORITHM_TYPE


class SENSORLOCATION(Enum):
    TOP_LEFT = 0
    BOTTOM_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_RIGHT = 3
    NONE = 4

    @staticmethod
    def get_sensor_location(value: int) -> 'SENSORLOCATION':
        return SENSORLOCATION(value)


@dataclass
class SensorData:
    timestamp: datetime.datetime
    serial_port: str
    location: SENSORLOCATION
    distance: int
    intensity: int
    temperature: int

    STRUCT_FORMAT = '<d 16s B H H H'  # timestamp, serial_port, location, distance, intensity, temperature

    def pack(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            self.timestamp.timestamp(),
            self.serial_port.encode('utf-8').ljust(16, b'\x00'),
            self.location.value,
            self.distance,
            self.intensity,
            self.temperature
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'SensorData':
        ts, port_bytes, loc, distance, intensity, temperature = struct.unpack(cls.STRUCT_FORMAT, data)
        return cls(
            timestamp=datetime.datetime.fromtimestamp(ts),
            serial_port=port_bytes.decode('utf-8').rstrip('\x00'),
            location=SENSORLOCATION.get_sensor_location(loc),
            distance=distance,
            intensity=intensity,
            temperature=temperature
        )

    @classmethod
    def get_total_size(cls):
        return struct.calcsize(cls.STRUCT_FORMAT)

    def getSensorLoc(self):
        return self.location



@dataclass
class ExperimentData():
    weights: List[int]

    STRUCT_FORMAT_EX = '<9H'

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT_EX, *self.weights)

    @classmethod
    def unpack(cls, data: bytes) -> 'ExperimentData':
        weights = list(struct.unpack(cls.STRUCT_FORMAT_EX, data))
        return cls(
            weights=weights
        )

    @classmethod
    def get_total_size(cls):
        return struct.calcsize(cls.STRUCT_FORMAT_EX)


@dataclass
class AlgorithmData():
    algo_type: 'ALGORITHM_TYPE'
    predicted_weight: int
    error: int
    position: int
    referenceValue: List[int]

    def __init__(self,
                 algo_type: 'ALGORITHM_TYPE' = None,
                 predicted_weight: int = 0,
                 error: int = 0,
                 position: int = -1,
                 refVal: List[int] = None):
        self.algo_type = algo_type
        self.predicted_weight = predicted_weight
        self.error = error
        self.position = position
        self.referenceValue = refVal

    STRUCT_FORMAT_ALGO = '<B H H H 9H'

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT_ALGO, self.algo_type.value, self.predicted_weight, self.error, self.position, *self.referenceValue)

    @classmethod
    def unpack(cls, data: bytes) -> 'AlgorithmData':
        unpacked = struct.unpack(cls.STRUCT_FORMAT_ALGO, data)
        algotype, pred_weight, error, position = unpacked[:4]
        refVal = list(unpacked[4:])
        return cls(
            algo_type=ALGORITHM_TYPE.get_algorithmTypebyValue(algotype),
            predicted_weight=pred_weight,
            error=error,
            position=position,
            refVal=refVal
        )

    @classmethod
    def get_total_size(cls):
        return struct.calcsize(cls.STRUCT_FORMAT_ALGO)


SCENARIO_TYPE_MAP = {
    1000: {
        "name": "None",
        "description": "시나리오 없음"
    },
    0: {
        "name": "center_concentrated",
        "description": "전방 중앙 집중 적재"
    },
    1: {
        "name": "vertical_center",
        "description": "중앙 세로 적재"
    },
    2: {
        "name": "sequential_front",
        "description": "전방부터 순차 적재"
    },
    3: {
        "name": "asymmetric_left_right",
        "description": "좌우 비대칭 적재"
    },
    4: {
        "name": "symmetric_front",
        "description": "전방 대칭 적재"
    }
}

REVERSE_SCENARIO_TYPE_MAP = {
    v["name"]: k for k, v in SCENARIO_TYPE_MAP.items()
}
REVERSE_SCENARIO_DESC_MAP = {
    v["description"]: k for k, v in SCENARIO_TYPE_MAP.items()
}

@dataclass
class SensorFrame:
    timestamp: datetime.datetime  # UNIX timestamp (int)
    sensors: List[SensorData]
    scenario: int  # Experiment Scenario
    NofExperiments: int
    started: bool   # 실험 시작 여부
    measured: bool  # 측정 시작 여부
    experiment: ExperimentData
    algorithms: AlgorithmData
    isEoF: bool = False

    def __init__(self,
                 timestamp: datetime.datetime,
                 sensors: List[SensorData],
                 scenario: int = 1000,
                 NofExperiments: int = 0,
                 started: bool = False,
                 measured: bool = False,
                 experiment: ExperimentData = None,
                 algorithms: AlgorithmData = None,
                 isEoF: bool = False):
        self.timestamp = timestamp
        self.scenario = scenario
        self.started = started
        self.NofExperiments = NofExperiments
        self.measured = measured
        self.sensors = sensors
        self.experiment = experiment
        self.algorithms = algorithms
        self.isEoF = isEoF

    STRUCT_HEADER_FORMAT = '<d H H ??'  # timestamp, scenario, started, measured

    def get_scenario_name(self) -> str:
        return SCENARIO_TYPE_MAP[self.scenario]["name"]

    def get_scenario_desc(self) -> str:
        return SCENARIO_TYPE_MAP[self.scenario]["description"]

    def get_sensor_data(self, sensor_location: SENSORLOCATION) -> SensorData:
        return self.sensors[sensor_location.value]

    def get_sensors(self):
        return self.sensors

    def pack(self) -> bytes:
        packed = struct.pack(
            self.STRUCT_HEADER_FORMAT,
            self.timestamp.timestamp(),
            self.scenario,
            self.NofExperiments,
            self.started,
            self.measured
        )
        for sensor in self.sensors:
            packed += sensor.pack()
        packed += self.experiment.pack()
        packed += self.algorithms.pack()
        return packed

    @classmethod
    def unpack(cls, f) -> 'SensorFrame':
        header_size = struct.calcsize(cls.STRUCT_HEADER_FORMAT)
        header = f.read(header_size)
        if not header:
            return None
        timestamp, scenario, NofExperiments, started, measured = struct.unpack(cls.STRUCT_HEADER_FORMAT, header)

        sensors = [SensorData.unpack(f.read(SensorData.get_total_size())) for _ in range(4)]
        experiment = ExperimentData.unpack(f.read(ExperimentData.get_total_size()))

        algorithms = AlgorithmData.unpack(f.read(AlgorithmData.get_total_size()))

        return cls(datetime.datetime.fromtimestamp(timestamp), sensors, scenario, NofExperiments, started, measured, experiment, algorithms)


class SensorBinaryFileHandler:
    def __init__(self, filename: str):
        self.filename = os.path.join("log", filename)
        self._lock = threading.Lock()
        self._buffer = deque()  # deque로 변경
        self._running = False
        self._thread = None
        self._metaData: SensorFrame = SensorFrame(None, None)

    def save_frames(self, frames: List[SensorFrame]):
        with open(self.filename, 'wb') as f:
            for frame in frames:
                f.write(frame.pack())

    def load_frames(self) -> List[SensorFrame]:
        frames = []
        with open(self.filename, 'rb') as f:
            while True:
                frame = SensorFrame.unpack(f)
                if frame is None:  # EOF
                    break
                frames.append(frame)
        return frames

    def start_auto_save(self, interval: float = 1.0, meta: SensorFrame = None):
        if meta is not None:
            self._setMetaData(meta, self._metaData)
        self._running = True
        self._thread = threading.Thread(target=self._auto_save_loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop_auto_save(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _setMetaData(self, src: SensorFrame, dest:SensorFrame):
        dest.scenario = src.scenario
        dest.NofExperiments = src.NofExperiments
        dest.started = src.started
        dest.measured = src.measured
        dest.experiment = src.experiment

    def setExperimentInfo(self, isExperimentStarted = None):
        if isExperimentStarted is not None:
            self._metaData.started = isExperimentStarted

    def add_frame(self, frame: SensorFrame):
        with self._lock:
            self._buffer.append(frame)

    def _auto_save_loop(self, interval: float):
        while self._running:
            time.sleep(interval)
            self._flush()

    def _flush(self):
        with self._lock:
            if not self._buffer:
                return
            with open(self.filename, 'ab') as f:
                while self._buffer:
                    f.write(self._buffer.popleft().pack())

    def isRunning(self) -> bool:
        return self._running

    def export_to_csv(self, csv_filename: str):
        frames = self.load_frames()
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Header
            writer.writerow([
                'timestamp', 'scenario', 'numofexperiments', 'started', 'measured',
                'sensor0_distance', 'sensor1_distance', 'sensor2_distance', 'sensor3_distance',
                'expW1','expW2','expW3','expW4','expW5','expW6','expW7','expW8','expW9',
                'algo_type', 'pred_weight', 'error','position','refV1','refV2','refV3','refV4',
                'refV5','refV6','refV7','refV8','refV9'
                # 필요시 더 추가 가능
            ])

            for frame in frames:
                row = [
                    frame.timestamp,
                    frame.scenario,
                    frame.NofExperiments,
                    frame.started,
                    frame.measured
                ]
                row.extend(sensor.distance for sensor in frame.sensors)
                row.extend(frame.experiment.weights)
                algo = frame.algorithms
                row.extend([algo.algo_type.name, algo.predicted_weight, algo.error, algo.position])
                row.extend(algo.referenceValue)
                writer.writerow(row)

class AlgorithmFileHandler(SensorBinaryFileHandler):
    def __init__(self, filename: str):
        super().__init__(filename)

    def setExperimentInfo(self, isExperimentStarted = None, isMeasureStarted = None):
        if isExperimentStarted is not None:
            self._metaData.started = isExperimentStarted

        if isMeasureStarted is not None:
            self._metaData.measured = isMeasureStarted

    def add_frame(self, frame: SensorFrame):
        self._setMetaData(self._metaData, frame)
        with self._lock:
            self._buffer.append(frame)

if __name__ == '__main__':
    # now = datetime.datetime.now()
    #
    # # 여러 개의 SensorFrame 생성
    # frames = []
    # for i in range(3):  # 예: 3개 프레임
    #     timestamp = (now + datetime.timedelta(seconds=i))
    #     #print(timestamp, type(timestamp), timestamp.timestamp(), type(timestamp.timestamp()))
    #     frame = SensorFrame(
    #         timestamp=timestamp,
    #         scenario=REVERSE_SCENARIO_TYPE_MAP['None'],
    #         sensors=[
    #             SensorData(timestamp, 'VCOM1', SENSORLOCATION.TOP_LEFT, 500 + i, 200 + i, 30 + i),
    #             SensorData(timestamp, 'VCOM2',SENSORLOCATION.BOTTOM_LEFT, 510 + i, 210 + i, 31 + i),
    #             SensorData(timestamp, 'VCOM3',SENSORLOCATION.TOP_RIGHT, 520 + i, 220 + i, 32 + i),
    #             SensorData(timestamp, 'VCOM4',SENSORLOCATION.BOTTOM_RIGHT, 530 + i, 230 + i, 33 + i),
    #         ],
    #         experiment=ExperimentData([20,40,20,0,0,0,0,0,0]),
    #         algorithms=[AlgorithmData(ALGORITHM_TYPE.COGMassEstimation, 20, 10, 1), AlgorithmData(ALGORITHM_TYPE.MLPPredictor, 20, 10, 1)]
    #     )
    #     frames.append(frame)
    #
    # # 파일에 저장
    # handler = SensorBinaryFileHandler('sensor_log.bin')
    # handler.save_frames(frames)
    handler = AlgorithmFileHandler('COGMassEstimation_asymmetric_left_right_20250424.bin')
    # 파일에서 불러오기
    loaded_frames = handler.load_frames()
    handler.export_to_csv('test.csv')
    # 출력
    for idx, f in enumerate(loaded_frames):
        print(f"\n[Frame {idx}] timestamp={f.timestamp}, expStarted={f.started}, isMeasured={f.measured}, scenario={f.get_scenario_name()}, experiment={f.experiment}, algorithms={f.algorithms}")
        for s in f.sensors:
            print(f"  - {type(s).__name__} @ {s.timestamp} @ {s.serial_port} @ {s.location.name}")
