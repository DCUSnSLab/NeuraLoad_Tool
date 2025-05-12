import os
import sys
import json
from scipy.stats import mode
import time
import numpy as np
from typing import Dict, List, Any, Optional

from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SensorFrame, SENSORLOCATION, AlgorithmData
from Algorithm.RefValueGenerator_COG import COGRefValGenerator
# 상위 디렉토리의 모듈을 import 하기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import datetime
from AlgorithmInterface import AlgorithmBase  # 상속용 추상 클래스


class COGPositionMassEstimation_v3(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="레이저 센서 변화량 기반 roll, pitch로 추정한 COG 좌표로 적재위치 및 무게 추정 알고리즘",
            refValGen = COGRefValGenerator()
        )

        self.loadingBoxWidth = 1630
        self.loadingBoxLength = 2860
        self.sensorCoords = np.array([
            [323.1, 1],  # TL (Top Left)
            [201, 2516.9],  # BL (Bottom Left)
            [1306.9, 1],  # TR (Top Right)
            [1429, 2516.9]  # BR (Bottom Right)
        ])
        self.sensorWeights = np.array([1.0, 0.45, 1.0, 0.45])  # 전방 센서 1.0, 후방 센서 0.45
        self.initial_laser_values = None

        self.locations = np.arange(1, 10)
        # 가중치 전방센서(1), 후방센서(0.45)
        self.initCenter = np.array([815, 1430, 0])
        self.xCenters = np.array([794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959, 834.6214622])
        self.yCenters = np.array([1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957, 1447.492051])
        self.zCenters = np.array([13.9859375, 15.51666667, 14.2640625, 16.65625, 16.3, 15.884375, 15.31041667, 17.61875, 15.29375])
        self.deltas = {i: [] for i in range(4)}
        self.alpha = 0.2
        self.previous_values = None
    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self, algo_data:AlgorithmData) -> AlgorithmData:
        deltas = self.preprocess_data(self.input_data, algo_data.referenceValue)
        xCenter, yCenter, zCenter = self.calculate_cog(deltas)
        location, weight = self.estimate_location_weight(xCenter, yCenter, zCenter)

        algo_data.algo_type = ALGORITHM_TYPE.COGPositionMassEstimation_v2
        algo_data.position = location
        algo_data.predicted_weight = weight
        algo_data.error = 0
        return algo_data

    def apply_lowpass_filter(self, current_values: List[float]) -> List[float]:
        if self.previous_values is None:
            self.previous_values = current_values
            return current_values

        filtered = [
            self.alpha * current_value + (1 - self.alpha) * prev_value
            for current_value, prev_value in zip(current_values, self.previous_values)
        ]
        self.previous_values = filtered
        return filtered

    def compute_deltas(self, current_values: List[float], init_value: List[float]) -> List[float]:
        deltas = [
            init - curr for curr, init in zip(current_values, init_value)
        ]
        return deltas

    def preprocess_data(self, frame: SensorFrame, init_value: List[float]) -> Dict[str, Any]:
        try:
            laser_values = [
                frame.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance,
                frame.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance,
                frame.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance,
                frame.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance,
            ]
        except Exception as e:
            return {'error': f'센서 데이터 추출 오류: {str(e)}'}

        deltas = self.compute_deltas(laser_values, init_value)
        weighted_deltas = np.array(deltas) * self.sensorWeights
        filtered_deltas = self.apply_lowpass_filter(weighted_deltas)

        for idx, change in enumerate(filtered_deltas):
            self.deltas[idx] = [change]

        return {
            'processed': True,
            'laser_values': laser_values,
            'deltas': filtered_deltas,
            'timestamp': frame.timestamp,
            'scenario': frame.get_scenario_name(),
            'measured': frame.measured
        }

    def calculate_cog(self, deltas: np.ndarray) -> (float, float, float):
        deltas = deltas['deltas']
        roll = ((deltas[0] - deltas[2]) + (deltas[1] - deltas[3])) / (((self.sensorCoords[3, 0] - self.sensorCoords[1, 0]) + (self.sensorCoords[2, 0] - self.sensorCoords[0, 0])) / 2)
        pitch = ((deltas[0] - deltas[1]) + (deltas[2] - deltas[3])) / (((self.sensorCoords[3, 1] - self.sensorCoords[2, 1]) + (self.sensorCoords[1, 1] - self.sensorCoords[0, 1])) / 2)
        x_center = (self.loadingBoxWidth / 2) - roll * (self.loadingBoxWidth / 2)
        y_center = (self.loadingBoxLength / 2) - pitch * (self.loadingBoxLength / 2)
        z_center = (deltas[0] + deltas[1] + deltas[2] + deltas[3]) / 4
        return x_center, y_center, z_center

    def estimate_location_weight(self, xCenter: float, yCenter: float, zCenter: float) -> (int, float):
        results = []
        current = np.array([xCenter, yCenter, zCenter])  # 3D 좌표
        distances = []

        # 각 위치에 대해 거리 계산
        for i, location in enumerate(self.locations):
            base = np.array([self.xCenters[i], self.yCenters[i], self.zCenters[i]])  # 3D 위치
            dist = np.linalg.norm(current - base)  # 3D 거리 계산
            distances.append((dist, location, i))

        distances.sort(key=lambda x: x[0])
        locations = distances[:2]

        total_distance = locations[0][0] + locations[1][0]
        ratio1 = locations[0][0] / total_distance
        ratio2 = locations[1][0] / total_distance

        location_candidates = []
        for _, location, i in locations:
            base = np.array([self.xCenters[i], self.yCenters[i], self.zCenters[i]])  # 3D 위치
            direction = base - self.initCenter  # 3D 방향 벡터
            if np.linalg.norm(direction) == 0:
                continue
            to_target = current - self.initCenter  # 3D 타겟 벡터
            projection_length = np.dot(to_target, direction) / np.linalg.norm(direction)
            if projection_length <= 0:
                continue
            scale = projection_length / np.linalg.norm(direction)
            weight = scale * 500
            direction_unit = direction / np.linalg.norm(direction)
            proj_vec = projection_length * direction_unit
            orth_dist = np.linalg.norm(to_target - proj_vec)

            location_candidates.append({
                "location": location,
                "weight": weight,
                "orth_dist": orth_dist
            })

        if len(location_candidates) < 1:
            print(f"[ERROR] No valid results to calculate weight.")
            return location, 0

        # 비율을 곱한 후 weight 합산
        if len(location_candidates) == 1:
            total_weight = location_candidates[0]["weight"]
        else:
            weight1 = location_candidates[0]["weight"] * ratio2
            weight2 = location_candidates[1]["weight"] * ratio1
            print("valid_candidates[0]: ", location_candidates[0]["location"], "valid_candidates[1]: ", location_candidates[1]["location"])
            total_weight = weight1 + weight2
            print(f"weight1: {weight1}, weight2: {weight2}, total_weight: {total_weight}")
        location = locations[0][1]
        print("select_location: ", location)
        return location, int(total_weight)