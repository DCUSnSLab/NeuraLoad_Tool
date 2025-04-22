from dataclasses import dataclass
from enum import Enum
from typing import List, BinaryIO
import struct
import datetime

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

    STRUCT_FORMAT = '<I 16s B H H H'  # timestamp, serial_port, location, distance, intensity, temperature

    def pack(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            int(self.timestamp),
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
            timestamp=ts,
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

    STRUCT_FORMAT_ALGO = '<B H H'

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT_ALGO, self.algo_type.value, self.predicted_weight, self.error)

    @classmethod
    def unpack(cls, data: bytes) -> 'AlgorithmData':
        algotype, pred_weight, error = struct.unpack(cls.STRUCT_FORMAT_ALGO, data)
        return cls(
            algo_type=ALGORITHM_TYPE.get_sensor_location(algotype),
            predicted_weight=pred_weight,
            error=error
        )

    @classmethod
    def get_total_size(cls):
        return struct.calcsize(cls.STRUCT_FORMAT_ALGO)


SCENARIO_TYPE_MAP = {
    -1: {
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
    started: bool   # 실험 시작 여부
    measured: bool  # 측정 시작 여부
    experiment: ExperimentData
    algorithms: List[AlgorithmData]

    def __init__(self,
                 timestamp: datetime.datetime,
                 sensors: List[SensorData],
                 scenario: int = -1,
                 started: bool = False,
                 measured: bool = False,
                 experiment: ExperimentData = None,
                 algorithms: List[AlgorithmData] = None):
        self.timestamp = timestamp
        self.scenario = scenario
        self.started = started
        self.measured = measured
        self.sensors = sensors
        self.experiment = experiment
        self.algorithms = algorithms

    STRUCT_HEADER_FORMAT = '<I H ??'  # timestamp, scenario, started, measured

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
            int(self.timestamp),
            self.scenario,
            self.started,
            self.measured
        )
        for sensor in self.sensors:
            packed += sensor.pack()
        packed += self.experiment.pack()
        packed += struct.pack('<B', len(self.algorithms))  # 알고리즘 수
        for algo in self.algorithms:
            packed += algo.pack()
        return packed

    @classmethod
    def unpack(cls, f) -> 'SensorFrame':
        header_size = struct.calcsize(cls.STRUCT_HEADER_FORMAT)
        header = f.read(header_size)
        if not header:
            return None
        timestamp, scenario, started, measured = struct.unpack(cls.STRUCT_HEADER_FORMAT, header)

        sensors = [SensorData.unpack(f.read(SensorData.get_total_size())) for _ in range(4)]
        experiment = ExperimentData.unpack(f.read(ExperimentData.get_total_size()))

        num_algos = struct.unpack('<B', f.read(1))[0]
        algorithms = [AlgorithmData.unpack(f.read(AlgorithmData.get_total_size())) for _ in range(num_algos)]

        return cls(timestamp, sensors, scenario, started, measured, experiment, algorithms)


class SensorBinaryFileHandler:
    def __init__(self, filename: str):
        self.filename = filename

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

if __name__ == '__main__':
    now = datetime.datetime.now()

    # 여러 개의 SensorFrame 생성
    frames = []
    for i in range(3):  # 예: 3개 프레임
        timestamp = (now + datetime.timedelta(seconds=i)).timestamp()
        frame = SensorFrame(
            timestamp=timestamp,
            scenario=REVERSE_SCENARIO_TYPE_MAP['sequential_front'],
            sensors=[
                SensorData(timestamp, 'VCOM1', SENSORLOCATION.TOP_LEFT, 500 + i, 200 + i, 30 + i),
                SensorData(timestamp, 'VCOM2',SENSORLOCATION.BOTTOM_LEFT, 510 + i, 210 + i, 31 + i),
                SensorData(timestamp, 'VCOM3',SENSORLOCATION.TOP_RIGHT, 520 + i, 220 + i, 32 + i),
                SensorData(timestamp, 'VCOM4',SENSORLOCATION.BOTTOM_RIGHT, 530 + i, 230 + i, 33 + i),
            ],
            experiment=ExperimentData([20,40,20,0,0,0,0,0,0]),
            algorithms=[AlgorithmData(ALGORITHM_TYPE.COGMassEstimation, 20, 10), AlgorithmData(ALGORITHM_TYPE.MLPPredictor, 20, 10)]
        )
        frames.append(frame)

    # 파일에 저장
    handler = SensorBinaryFileHandler('sensor_log.bin')
    handler.save_frames(frames)

    # 파일에서 불러오기
    loaded_frames = handler.load_frames()

    # 출력
    for idx, f in enumerate(loaded_frames):
        print(f"\n[Frame {idx}] timestamp={f.timestamp}, scenario={f.get_scenario_name()}, experiment={f.experiment}, algorithms={f.algorithms}")
        for s in f.sensors:
            print(f"  - {type(s).__name__} @ {s.timestamp} @ {s.serial_port} @ {s.location.name}")
