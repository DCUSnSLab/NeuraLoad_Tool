from dataclasses import dataclass
from enum import Enum
from typing import List, BinaryIO
import struct
import datetime

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
    timestamp: int
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



@dataclass(init=False)
class ExperimentData(SensorData):
    weights: List[int]

    STRUCT_FORMAT_EX = '<9H'

    def __init__(self, timestamp, serial_port, location, distance, intensity, temperature, weights=None):
        super().__init__(timestamp, serial_port, location, distance, intensity, temperature)
        self.weights = weights if weights is not None else [0] * 9

    def pack(self) -> bytes:
        return super().pack() + struct.pack(self.STRUCT_FORMAT_EX, *self.weights)

    @classmethod
    def unpack(cls, data: bytes) -> 'ExperimentData':
        base_size = SensorData.get_total_size()
        base = SensorData.unpack(data[:base_size])
        weights = list(struct.unpack(cls.STRUCT_FORMAT_EX, data[base_size:]))
        return cls(
            timestamp=base.timestamp,
            serial_port=base.serial_port,
            location=base.location,
            distance=base.distance,
            intensity=base.intensity,
            temperature=base.temperature,
            weights=weights
        )

    @classmethod
    def get_total_size(cls):
        return SensorData.get_total_size() + struct.calcsize(cls.STRUCT_FORMAT_EX)

    @classmethod
    def from_sensor(cls, sensor_data: SensorData, weights: List[int] = None):
        return cls(
            timestamp=sensor_data.timestamp,
            serial_port=sensor_data.serial_port,
            location=sensor_data.location,
            distance=sensor_data.distance,
            intensity=sensor_data.intensity,
            temperature=sensor_data.temperature,
            weights=weights
        )


@dataclass
class AlgorithmData(ExperimentData):
    predicted_weight: int
    error: int

    STRUCT_FORMAT_ALGO = '<H H'

    def pack(self) -> bytes:
        return super().pack() + struct.pack(self.STRUCT_FORMAT_ALGO, self.predicted_weight, self.error)

    @classmethod
    def unpack(cls, data: bytes) -> 'AlgorithmData':
        base_size = ExperimentData.get_total_size()
        base = ExperimentData.unpack(data[:base_size])
        pred_weight, error = struct.unpack(cls.STRUCT_FORMAT_ALGO, data[base_size:])
        return cls(
            timestamp=base.timestamp,
            serial_port=base.serial_port,
            location=base.location,
            distance=base.distance,
            intensity=base.intensity,
            temperature=base.temperature,
            weights=base.weights,
            is_experiment=base.is_experiment,
            predicted_weight=pred_weight,
            error=error
        )

    @classmethod
    def get_total_size(cls):
        return ExperimentData.get_total_size() + struct.calcsize(cls.STRUCT_FORMAT_ALGO)

    @classmethod
    def from_sensor(cls, sensor_data: SensorData,
                    weights: List[int] = None,
                    is_experiment: bool = False,
                    predicted_weight: int = 0,
                    error: int = 0) -> 'AlgorithmData':
        return cls(
            timestamp=sensor_data.timestamp,
            serial_port=sensor_data.serial_port,
            location=sensor_data.location,
            distance=sensor_data.distance,
            intensity=sensor_data.intensity,
            temperature=sensor_data.temperature,
            weights=weights,
            is_experiment=is_experiment,
            predicted_weight=predicted_weight,
            error=error
        )

DATA_TYPE_MAP = {
    0: SensorData,
    1: ExperimentData,
    2: AlgorithmData
}
REVERSE_TYPE_MAP = {v: k for k, v in DATA_TYPE_MAP.items()}

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
    timestamp: int  # UNIX timestamp (int)
    scenario: int  # Experiment Scenario
    started: bool   # 실험 시작 여부
    measured: bool  # 측정 시작 여부
    sensors: List[SensorData]

    STRUCT_HEADER_FORMAT = '<I H ??'  # timestamp, scenario, started, measured

    def __init__(self, timestamp: int, sensors: List[SensorData], scenario: int = -1, started: bool = False, measured: bool = False):
        self.timestamp = timestamp
        self.scenario = scenario
        self.started = started
        self.measured = measured
        self.sensors = sensors

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
            self.timestamp,
            self.scenario,
            self.started,
            self.measured
        )
        for sensor in self.sensors:
            dtype = REVERSE_TYPE_MAP[type(sensor)]
            sensor_data = sensor.pack()
            packed += struct.pack('<B', dtype) + sensor_data
        return packed

    @staticmethod
    def unpack(f: BinaryIO) -> 'SensorFrame':
        header_size = struct.calcsize(SensorFrame.STRUCT_HEADER_FORMAT)
        header_data = f.read(header_size)
        if not header_data:
            return None
        if len(header_data) < header_size:
            raise ValueError("불완전한 SensorFrame 헤더")

        timestamp, scenario, started, measured = struct.unpack(SensorFrame.STRUCT_HEADER_FORMAT, header_data)

        sensors = []
        for _ in range(4):
            dtype_data = f.read(1)
            if not dtype_data:
                raise ValueError("센서 타입 누락")
            dtype = struct.unpack('<B', dtype_data)[0]
            cls = DATA_TYPE_MAP.get(dtype)
            if cls is None:
                raise ValueError(f"알 수 없는 센서 타입 코드: {dtype}")
            sensor_bytes = f.read(cls.get_total_size())
            if len(sensor_bytes) < cls.get_total_size():
                raise ValueError("불완전한 센서 데이터")
            sensor = cls.unpack(sensor_bytes)
            sensors.append(sensor)

        return SensorFrame(timestamp, scenario, started, measured, sensors)


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
        timestamp = int((now + datetime.timedelta(seconds=i)).timestamp())
        frame = SensorFrame(
            timestamp=timestamp,
            scenario=REVERSE_SCENARIO_TYPE_MAP['sequential_front'],
            sensors=[
                SensorData(timestamp, 'VCOM1', SENSORLOCATION.TOP_LEFT, 500 + i, 200 + i, 30 + i),
                ExperimentData(timestamp, 'VCOM2',SENSORLOCATION.BOTTOM_LEFT, 510 + i, 210 + i, 31 + i, [101 + i] * 9, i % 2 == 0),
                AlgorithmData(timestamp, 'VCOM3',SENSORLOCATION.TOP_RIGHT, 520 + i, 220 + i, 32 + i, [102 + i] * 9, True, 850 + i, 5 + i),
                AlgorithmData(timestamp, 'VCOM4',SENSORLOCATION.BOTTOM_RIGHT, 530 + i, 230 + i, 33 + i, [103 + i] * 9, False, 870 + i, 6 + i),
            ]
        )
        frames.append(frame)

    # 파일에 저장
    handler = SensorBinaryFileHandler('sensor_log.bin')
    handler.save_frames(frames)

    # 파일에서 불러오기
    loaded_frames = handler.load_frames()

    # 출력
    for idx, f in enumerate(loaded_frames):
        print(f"\n[Frame {idx}] timestamp={f.timestamp}, scenario={f.get_scenario_name()}")
        for s in f.sensors:
            print(f"  - {type(s).__name__} @ {s.timestamp} @ {s.serial_port} @ {s.location.name}")
