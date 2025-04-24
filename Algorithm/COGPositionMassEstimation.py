import os
import sys
import json
from scipy.stats import mode
import time
import numpy as np
from typing import Dict, List, Any, Optional

from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SensorFrame, SENSORLOCATION, AlgorithmData

# 상위 디렉토리의 모듈을 import 하기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import datetime
from AlgorithmInterface import AlgorithmBase  # 상속용 추상 클래스

class COGPositionMassEstimation(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="레이저 센서 변화량 기반 roll, pitch로 추정한 COG 좌표로 적재위치 및 무게 추정 알고리즘"
        )
        self.initCenter = np.array([815, 1430])  # 초기 중심 좌표
        self.loadingBoxWidth = 1630
        self.loadingBoxLength = 2860
        self.sensorCoords = np.array([
            [131, 440.95],     # TL (Top Left)
            [389, 2660.75],    # BL (Bottom Left)
            [1499, 365.25],    # TR (Top Right)
            [1241, 2660.75]    # BR (Bottom Right)
        ])
        self.sensorWeights = np.array([1.0, 0.6, 1.0, 0.6])  # 전방 센서 1.0, 후방 센서 0.6
        self.initial_laser_values = None

        # 위치별 기준 무게중심 좌표
        self.locations = np.arange(1, 10)
        self.xCenters = np.array([792.7, 813.5, 834.3, 793.7, 814.3, 834.8, 794.9, 815.1, 835.3])
        self.yCenters = np.array([1417.5, 1430.5, 1443.5, 1456.5, 1469.5, 1482.5, 1495.6, 1508.6, 1521.6])
    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self) -> AlgorithmData:
        if self.input_data is None:
            raise Exception("Input data is None")

        processed = self.preprocess_data(self.input_data)
        if 'error' in processed:
            return processed

        deltas = processed['delta_values']
        roll, pitch = self.calculate_roll_pitch(deltas)
        xCenter, yCenter = self.calculate_cog(roll, pitch)
        location, weight = self.estimate_location_weight(xCenter, yCenter)
        return AlgorithmData(algo_type=ALGORITHM_TYPE.COGPositionMassEstimation,
                             predicted_weight=weight,
                             error=0,
                             position=location)
        # return {
        #     "roll": roll,
        #     "pitch": pitch,
        #     "xCenter": xCenter,
        #     "yCenter": yCenter,
        #     "location": location,
        #     "weight": weight
        # }

    def compute_deltas(self, current_values: List[float]) -> List[float]:
        if self.initial_laser_values is None:
            if all(v not in [-1, 0] for v in current_values):
                self.initial_laser_values = current_values
            return [0.0] * len(current_values)

        return [init - curr for init, curr in zip(self.initial_laser_values, current_values)]

    def preprocess_data(self, frame: SensorFrame) -> Dict[str, Any]:
        try:
            laser_values = [
                frame.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance,
                frame.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance,
                frame.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance,
                frame.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance,
            ]
        except Exception as e:
            return {'error': f'센서 데이터 추출 오류: {str(e)}'}

        deltas = self.compute_deltas(laser_values)
        weighted_deltas = np.array(deltas) * self.sensorWeights

        return {
            'laser_values': laser_values,
            'delta_values': weighted_deltas,
            'timestamp': frame.timestamp,
            'scenario': frame.get_scenario_name(),
            'measured': frame.measured
        }

    def calculate_roll_pitch(self, deltas: np.ndarray) -> (float, float):
        roll = ((deltas[0] + deltas[1]) - (deltas[2] + deltas[3])) / 2860
        pitch = ((deltas[0] + deltas[2]) - (deltas[1] + deltas[3])) / 1630
        return roll, pitch

    def calculate_cog(self, roll: float, pitch: float) -> (float, float):
        x = (self.loadingBoxWidth / 2) - roll * (self.loadingBoxWidth / 2)
        y = (self.loadingBoxLength / 2) - pitch * (self.loadingBoxLength / 2)
        return x, y

    def estimate_location_weight(self, xCenter: float, yCenter: float) -> (int, float):
        results = []
        current = np.array([xCenter, yCenter])
        for i, location in enumerate(self.locations):
            base = np.array([self.xCenters[i], self.yCenters[i]])
            direction = base - self.initCenter
            if np.linalg.norm(direction) == 0:
                continue
            to_target = current - self.initCenter
            projection = np.dot(to_target, direction) / np.linalg.norm(direction)
            if projection <= 0:
                continue
            scale = projection / np.linalg.norm(direction)
            weight = scale * 500
            proj_vec = np.dot(to_target, direction / np.linalg.norm(direction)) * (direction / np.linalg.norm(direction))
            orth_dist = np.linalg.norm(to_target - proj_vec)
            results.append((location, weight, orth_dist))

        if not results:
            return 5, 0.0  # 중심 위치에 가까운 경우 default

        location, weight, _ = min(results, key=lambda x: x[2])

        return location, int(weight)
