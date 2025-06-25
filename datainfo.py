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
    
    #조도센서관련데이터터
    lux: float = 0.0
    gainMultiplier: float = 0.0
    integrationTime: float = 0.0
    cpl: float = 0.0
    visible: int = 0
    ch0: int = 0
    ch1: int = 0
    fullLuminosity: int = 0

    STRUCT_FORMAT = '<d 16s B H H H f f f f H H H H'  # timestamp, serial_port, location, distance, intensity, temperature, lux, gainMultiplier, integrationTime, cpl, visible, ch0, ch1, fullLuminosity

    def pack(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            self.timestamp.timestamp(),
            self.serial_port.encode('utf-8').ljust(16, b'\x00'),
            self.location.value,
            self.distance,
            self.intensity,
            self.temperature,
            self.lux,
            self.gainMultiplier,
            self.integrationTime,
            self.cpl,
            self.visible,
            self.ch0,
            self.ch1,
            self.fullLuminosity
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'SensorData':
        ts, port_bytes, loc, distance, intensity, temperature, lux, gainMultiplier, integrationTime, cpl, visible, ch0, ch1, fullLuminosity = struct.unpack(cls.STRUCT_FORMAT, data)
        return cls(
            timestamp=datetime.datetime.fromtimestamp(ts),
            serial_port=port_bytes.decode('utf-8').rstrip('\x00'),
            location=SENSORLOCATION.get_sensor_location(loc),
            distance=distance,
            intensity=intensity,
            temperature=temperature,
            lux=lux,
            gainMultiplier=gainMultiplier,
            integrationTime=integrationTime,
            cpl=cpl,
            visible=visible,
            ch0=ch0,
            ch1=ch1,
            fullLuminosity=fullLuminosity
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

    STRUCT_FORMAT_ALGO = '<B H H H'

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT_ALGO, self.algo_type.value, self.predicted_weight, self.error, self.position)

    @classmethod
    def unpack(cls, data: bytes) -> 'AlgorithmData':
        algotype, pred_weight, error, position = struct.unpack(cls.STRUCT_FORMAT_ALGO, data)
        return cls(
            algo_type=ALGORITHM_TYPE.get_algorithmTypebyValue(algotype),
            predicted_weight=pred_weight,
            error=error,
            position=position
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
            
            header = ['timestamp', 'scenario', 'numofexperiments', 'started', 'measured']
            
            for i in range(4):
                sensor_prefix = f'sensor{i}'
                header.extend([
                    f'{sensor_prefix}_distance', f'{sensor_prefix}_intensity', f'{sensor_prefix}_temperature',
                    f'{sensor_prefix}_lux', f'{sensor_prefix}_gainMultiplier', f'{sensor_prefix}_integrationTime',
                    f'{sensor_prefix}_cpl', f'{sensor_prefix}_visible', f'{sensor_prefix}_ch0',
                    f'{sensor_prefix}_ch1', f'{sensor_prefix}_fullLuminosity'
                ])
            
            header.extend(['expW1','expW2','expW3','expW4','expW5','expW6','expW7','expW8','expW9'])
            header.extend(['algo_type', 'pred_weight', 'error','position'])
            
            writer.writerow(header)

            for frame in frames:
                row = [
                    frame.timestamp,
                    frame.scenario,
                    frame.NofExperiments,
                    frame.started,
                    frame.measured
                ]
                
                for sensor in frame.sensors:
                    row.extend([
                        sensor.distance, sensor.intensity, sensor.temperature,
                        sensor.lux, sensor.gainMultiplier, sensor.integrationTime,
                        sensor.cpl, sensor.visible, sensor.ch0,
                        sensor.ch1, sensor.fullLuminosity
                    ])
                
                row.extend(frame.experiment.weights)
                algo = frame.algorithms
                row.extend([algo.algo_type.name, algo.predicted_weight, algo.error, algo.position])
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
    # 새로운 형식 테스트를 위한 샘플 데이터 생성
    now = datetime.datetime.now()
    
    # 여러 개의 SensorFrame 생성 (새로운 11개 필드 포함)
    frames = []
    for i in range(3):  # 예: 3개 프레임
        timestamp = (now + datetime.timedelta(seconds=i))
        sensors = []
        
        # 4개 센서 데이터 생성 (11개 필드 모두 포함)
        for j in range(4):
            sensor_data = SensorData(
                timestamp=timestamp,
                serial_port=f'VCOM{j+1}',
                location=SENSORLOCATION.get_sensor_location(j),
                distance=500 + i + j*10,
                intensity=200 + i + j*10,
                temperature=30 + i,
                lux=100.0 + i*50 + j*25,
                gainMultiplier=1.0 + j*2,
                integrationTime=50.0 + i*10,
                cpl=1.0 + j*0.5,
                visible=1000 + i*100 + j*200,
                ch0=500 + i*50 + j*100,
                ch1=200 + i*25 + j*50,
                fullLuminosity=2000 + i*200 + j*300
            )
            sensors.append(sensor_data)
        
        frame = SensorFrame(
            timestamp=timestamp,
            scenario=REVERSE_SCENARIO_TYPE_MAP['None'],
            sensors=sensors,
            experiment=ExperimentData([20,40,20,0,0,0,0,0,0]),
            algorithms=AlgorithmData(ALGORITHM_TYPE.COGMassEstimation, 20, 10, 1)
        )
        frames.append(frame)

    # 새로운 형식으로 파일에 저장
    print("new format data saved")
    handler = AlgorithmFileHandler('raw_data_2025-06-25.bin')
    handler.save_frames(frames)
    
    loaded_frames = handler.load_frames()
    
    # CSV로 내보내기
    print("CSV file created")
    handler.export_to_csv('raw_data_2025-06-25.csv')
    
    # 출력
    print(f"\n{len(loaded_frames)} frames loaded")
    for idx, f in enumerate(loaded_frames):
        print(f"\n[Frame {idx}] timestamp={f.timestamp}, scenario={f.get_scenario_name()}")
        for s in f.sensors:
            print(f"  - {s.serial_port} @ {s.location.name}: dist={s.distance}, temp={s.temperature}, lux={s.lux:.1f}")
    