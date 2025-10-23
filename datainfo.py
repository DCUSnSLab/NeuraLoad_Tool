import csv
import datetime
import os
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import List

from Algorithm.algorithmtype import ALGORITHM_TYPE


class SENSORLOCATION(Enum):
    TOP_LEFT     = 0
    BOTTOM_LEFT  = 1
    TOP_RIGHT    = 2
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
    distance: float  # Laser Sensor Data
    intensity: float
    temperature: float
    lux: float  # Light Sensor Data
    ch0: int
    ch1: int

    # timestamp, serial_port, location
    # Laser Sensor Data : distance, intensity, temperature
    # Light Sensor Data : lux, ch0, ch1
    STRUCT_FORMAT = '<d 16s B d d d d H H'

    def pack(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            self.timestamp.timestamp(),
            self.serial_port.encode('utf-8').ljust(16, b'\x00'),
            self.location.value,
            self.distance,  # Laser Sensor
            self.intensity,
            self.temperature,
            self.lux,  # Light Sensor
            self.ch0,
            self.ch1,
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'SensorData':
        (
            ts, port_bytes, loc,
            distance, intensity, temperature,
            lux, ch0, ch1
        ) = struct.unpack(cls.STRUCT_FORMAT, data)

        return cls(
            timestamp=datetime.datetime.fromtimestamp(ts),
            serial_port=port_bytes.decode('utf-8').rstrip('\x00'),
            location=SENSORLOCATION.get_sensor_location(loc),
            distance=distance,  # Laser Sensor
            intensity=intensity,
            temperature=temperature,
            lux=lux,  # Light Sensor
            ch0=ch0,
            ch1=ch1
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
                 refVal: List[int] = [0] * 4):
        self.algo_type = algo_type
        self.predicted_weight = predicted_weight
        self.error = error
        self.position = position
        self.referenceValue = refVal

    STRUCT_FORMAT_ALGO = '<B h h H 4h'

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT_ALGO, self.algo_type.value, int(self.predicted_weight), self.error,
                           self.position, *self.referenceValue)

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
        "name": "asymmetric_left",
        "description": "좌측 비대칭 적재"
    },
    4: {
        "name": "symmetric_front",
        "description": "전방 대칭 적재"
    },
    5: {"name": "asymmetric_right",
        "description": "우측 비대칭 적재"
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
    started: bool  # 실험 시작 여부
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

        return cls(datetime.datetime.fromtimestamp(timestamp), sensors, scenario, NofExperiments, started, measured,
                   experiment, algorithms)


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

    def _setMetaData(self, src: SensorFrame, dest: SensorFrame):
        dest.scenario = src.scenario
        dest.NofExperiments = src.NofExperiments
        dest.started = src.started
        dest.measured = src.measured
        dest.experiment = src.experiment

    def setExperimentInfo(self, isExperimentStarted=None):
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
                'sensor0_lux', 'sensor1_lux', 'sensor2_lux', 'sensor3_lux',
                'expW1', 'expW2', 'expW3', 'expW4', 'expW5', 'expW6', 'expW7', 'expW8', 'expW9',
                'algo_type', 'pred_weight', 'error', 'position', 'refV1', 'refV2', 'refV3', 'refV4',
                'refV5', 'refV6', 'refV7', 'refV8', 'refV9'
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

    #
    # def import_from_csv(self, csv_filename: str) -> List[SensorFrame]:
    #     frames = []
    #     with open(csv_filename, newline='') as csvfile:
    #         reader = csv.DictReader(csvfile)
    #         for row in reader:
    #             timestamp_str = row['timestamp']
    #             # 문자열을 datetime 객체로 변환 (예: "2025-05-15 13:20:00")
    #             timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    #
    #             scenario = int(row['scenario'])
    #             NofExperiments = int(row['numofexperiments'])
    #             started = row['started'].lower() == 'true'
    #             measured = row['measured'].lower() == 'true'
    #
    #             sensors = []
    #             for i in range(4):
    #                 dist = float(row[f'sensor{i}_distance'])
    #                 # SensorData 생성법에 맞게 수정 필요
    #                 sensors.append(SensorData(distance=dist))
    #
    #             weights = [float(row[f'expW{i}']) for i in range(1, 10)]
    #
    #             algo_type_name = row['algo_type']
    #             # ALGORITHM_TYPE 변환 필요하면 여기서 처리
    #             predicted_weight = float(row['pred_weight'])
    #             error = float(row['error'])
    #             position = int(row['position'])
    #             ref_vals = [float(row[f'refV{i}']) for i in range(1, 10)]
    #
    #             algorithms = AlgorithmData(
    #                 algo_type=algo_type_name,
    #                 predicted_weight=predicted_weight,
    #                 error=error,
    #                 position=position,
    #                 refVal=ref_vals
    #             )
    #
    #             experiment = ExperimentData(weights=weights)
    #
    #             frame = SensorFrame(
    #                 timestamp=timestamp,
    #                 sensors=sensors,
    #                 scenario=scenario,
    #                 NofExperiments=NofExperiments,
    #                 started=started,
    #                 measured=measured,
    #                 experiment=experiment,
    #                 algorithms=algorithms,
    #                 serial_port='',  # CSV에 없으면 빈 문자열이나 기본값
    #                 location='',
    #                 distance=dist,
    #                 intensity=0,
    #                 temperature=0
    #             )
    #             frames.append(frame)
    #     return frames

    def import_from_csv(self, csv_filename: str, bin_filename: str):
        frames = []
        with open(csv_filename, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                time_str = row['timestamp']  # 예: '2025-05-16 0'

                try:
                    # 날짜+시간 형식으로 파싱 (예: '2025-05-16 0' 또는 '2025-05-16 00:26:09')
                    timestamp = datetime.datetime.strptime(time_str, '%Y-%m-%d %H')
                except ValueError:
                    # 예외 발생 시 다른 형식 시도하거나 기본값 처리
                    timestamp = datetime.datetime.now()  # 임시로 현재 시간 지정

                scenario = int(row['scenario'])
                NofExperiments = int(row['numofexperiments'])
                started = row['started'].lower() == 'true'
                measured = row['measured'].lower() == 'true'

                sensors = []
                for i in range(4):
                    distance = float(row[f'sensor{i}_distance'])
                    lux = float(row[f'sensor{i}_lux'])
                    sensors.append(SensorData(
                        timestamp=timestamp,
                        serial_port='',
                        location=SENSORLOCATION(i),
                        distance=distance,
                        intensity=0,
                        temperature=0,
                        lux=lux
                    ))

                weights = [int(row[f'expW{i}']) for i in range(1, 10)]
                experiment = ExperimentData(weights=weights)

                algo_type = ALGORITHM_TYPE[row['algo_type']]
                predicted_weight = int(row['pred_weight'])
                error = int(row['error'])
                position = int(row['position'])
                refVal = [int(row[f'refV{i}']) for i in range(1, 5)]
                algorithms = AlgorithmData(
                    algo_type=algo_type,
                    predicted_weight=predicted_weight,
                    error=error,
                    position=position,
                    refVal=refVal
                )

                frame = SensorFrame(
                    timestamp=timestamp,
                    sensors=sensors,
                    scenario=scenario,
                    NofExperiments=NofExperiments,
                    started=started,
                    measured=measured,
                    experiment=experiment,
                    algorithms=algorithms,
                    isEoF=False
                )
                frames.append(frame)

        handler = SensorBinaryFileHandler(bin_filename)
        handler.save_frames(frames)


class AlgorithmFileHandler(SensorBinaryFileHandler):
    def __init__(self, filename: str):
        super().__init__(filename)

    def setExperimentInfo(self, isExperimentStarted=None, isMeasureStarted=None):
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
    #
    # # handler = AlgorithmFileHandler('re_sequential_front_20250515.bin')
    # handler = AlgorithmFileHandler('re_COGPositionMassEstimation_v3_center_concentrated_20250428.bin')
    # # 파일에서 불러오기
    # loaded_frames = handler.load_frames()
    # handler.export_to_csv('re_COGPositionMassEstimation_v3_center_concentrated_20250428.csv')
    # # 출력
    # for idx, f in enumerate(loaded_frames):
    #     print(f"\n[Frame {idx}] timestamp={f.timestamp}, expStarted={f.started}, isMeasured={f.measured}, scenario={f.get_scenario_name()}, experiment={f.experiment}, algorithms={f.algorithms}")
    #     for s in f.sensors:
    #         print(f"  - {type(s).__name__} @ {s.timestamp} @ {s.serial_port} @ {s.location.name}")
    # #
    # # handler = AlgorithmFileHandler('re_sequential_front_20250515.bin')  # 저장할 파일명 지정
    # #     # frames = handler.import_from_csv('re_COGPositionMassEstimation_v3_v3_sequential_front_20250515.csv')
    # #     # handler.save_frames(frames)  # 파일 이름 없이 frames만 넘김
    #
    #
    #

    handler = AlgorithmFileHandler('raw_data_2025-09-10.bin')
    # 파일에서 불러오기
    loaded_frames = handler.load_frames()
    handler.export_to_csv('raw_data_2025-09-10.csv')
    # 출력
    for idx, f in enumerate(loaded_frames):
        print(
            f"\n[Frame {idx}] timestamp={f.timestamp}, expStarted={f.started}, isMeasured={f.measured}, scenario={f.get_scenario_name()}, experiment={f.experiment}, algorithms={f.algorithms}")
        for s in f.sensors:
            print(f"  - {type(s).__name__} @ {s.timestamp} @ {s.serial_port} @ {s.location.name}")

    # handler.import_from_csv('COGPositionMassEstimation_v3_symmetric_front_20250531.csv', 'COGPositionMassEstimation_v3_symmetric_front_20250531_1.bin')
