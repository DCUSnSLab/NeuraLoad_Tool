import os
import sys
import json
from scipy.stats import mode
import time
import numpy as np
from typing import Dict, List, Any, Optional
from collections import deque
from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SensorFrame, SENSORLOCATION, AlgorithmData
from Algorithm.RefValueGenerator_COG import COGRefValGenerator
# 상위 디렉토리의 모듈을 import 하기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import datetime
from AlgorithmInterface import AlgorithmBase  # 상속용 추상 클래스


class COGPositionMassEstimation_v7(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="레이저 센서 변화량 기반 roll, pitch로 추정한 COG 좌표로 적재위치 및 무게 추정 알고리즘",
            refValGen = COGRefValGenerator()
        )
        self.loadingBoxWidth = 1630
        self.loadingBoxLength = 2860
        self.sensorCoords = np.array([
            [373.1, 1],  # TL (Top Left)
            [201, 2516.9],  # BL (Bottom Left)
            [1256.9, 1],  # TR (Top Right)
            [1429, 2516.9]  # BR (Bottom Right)
        ])

        self.initial_laser_values = None

        self.locations = np.arange(1, 10)
        # 가중치 전방센서(1), 후방센서(0.45)
        self.sensorWeights = np.array([1.0, 0.45, 1.0, 0.45])
        self.initCenter = np.array([815, 1430, 0])
        self.xCenters = np.array([794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959, 834.6214622])
        self.yCenters = np.array([1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957, 1447.492051])
        self.zCenters = np.array([13.9859375, 15.51666667, 14.2640625, 16.65625, 16.3, 15.884375, 15.31041667, 15.61875, 15.29375])
        # self.coefficient = np.array([25.19912165, 22.38238093, 25.0243015, 17.15413477, 17.76075778, 17.89237431, 15.33267897, 13.92290494, 15.29881389])
        self.coefficient = np.array([34.305925, 31.019686, 33.7840643, 28.4172494, 28.3819276, 29.24740398, 29.14227469, 25.70094819, 29.02068168])
        self.deltas = {i: [] for i in range(4)}

        self.alpha = 0.2
        self.previous_values = None

        self.window_size = 30
        self.value_buffer = None

    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self, algo_data: AlgorithmData) -> AlgorithmData:
        deltas = self.preprocess_data(self.input_data, algo_data.referenceValue)
        xCenter, yCenter, zCenter = self.calculate_cog(deltas)
        location, weight = self.estimate_location_weight(xCenter, yCenter, zCenter)
        algo_data.algo_type = ALGORITHM_TYPE.COGPositionMassEstimation_v7
        algo_data.position = location
        algo_data.predicted_weight = weight
        algo_data.error = 0
        return algo_data


    def apply_moving_average_filter(self, current_values: List[float]) -> List[float]:
        if self.value_buffer is None:
            self.value_buffer = [deque(maxlen=self.window_size) for _ in current_values]

        for i, value in enumerate(current_values):
            self.value_buffer[i].append(value)

        filtered = [sum(buf) / len(buf) for buf in self.value_buffer]
        return filtered

    def compute_deltas(self, current_values: List[float], init_value: List[float]) -> List[float]:
        deltas = [
            init - curr for curr, init in zip(current_values, init_value)
        ]
        return deltas


    def preprocess_data(self, frame: SensorFrame, init_value: List[float]) -> Dict[str, Any]:
        try:
            laser_values = [0,0,0,0]
            for i in range(4):
                laser_values[i] = frame.get_sensor_data(SENSORLOCATION.get_sensor_location(i)).distance

        except Exception as e:
            return {'error': f'센서 데이터 추출 오류: {str(e)}'}
        if init_value and all(v > 0 for v in init_value):
            laser_values = self.apply_moving_average_filter(laser_values)
        deltas = self.compute_deltas(laser_values, init_value)
        filtered_deltas = np.array(deltas, dtype=np.float64) * self.sensorWeights
        # weighted_deltas = np.array(deltas) * self.sensorWeights
        # filtered_deltas = self.apply_moving_average_filter(weighted_deltas)

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
        filtered_deltas = np.array(deltas, dtype=np.float64) * self.sensorWeights
        roll = ((filtered_deltas[0] - filtered_deltas[2]) + (filtered_deltas[1] - filtered_deltas[3])) / (((self.sensorCoords[3, 0] - self.sensorCoords[1, 0]) + (self.sensorCoords[2, 0] - self.sensorCoords[0, 0])) / 2)
        pitch = ((filtered_deltas[0] - filtered_deltas[1]) + (filtered_deltas[2] - filtered_deltas[3])) / (((self.sensorCoords[3, 1] - self.sensorCoords[2, 1]) + (self.sensorCoords[1, 1] - self.sensorCoords[0, 1])) / 2)
        x_center = (self.loadingBoxWidth / 2) - roll * (self.loadingBoxWidth / 2)
        y_center = (self.loadingBoxLength / 2) - pitch * (self.loadingBoxLength / 2)
        z_center = (deltas[0] + deltas[1] + deltas[2] + deltas[3]) / 4
        return x_center, y_center, z_center

    def estimate_location(self, xCenter: float, yCenter: float):
        point = np.array([xCenter, yCenter])

        # 5번을 제외한 인덱스 리스트
        non_center_indices = [i for i, loc in enumerate(self.locations) if loc != 5]

        # 모든 위치(5번 제외)와의 거리 계산
        distances = [
            (np.linalg.norm(point - np.array([self.xCenters[i], self.yCenters[i]])), i)
            for i in non_center_indices
        ]
        closest_dist, closest_idx = min(distances, key=lambda x: x[0])
        closest_loc = self.locations[closest_idx]

        # 인접 위치 매핑
        neighbors = {
            1: [2, 4],
            2: [1, 3],
            3: [2, 6],
            4: [1, 7],
            6: [3, 9],
            7: [4, 8],
            8: [7, 9],
            9: [6, 8]
        }

        adjacents = neighbors.get(closest_loc, [])
        if not adjacents:
            return [(0, closest_loc, closest_idx)]

        # 인접 위치들 중에서 가장 가까운 것 찾기
        candidate_segments = []
        for adj in adjacents:
            adj_idx = self.locations.tolist().index(adj)
            dist = np.linalg.norm(point - np.array([self.xCenters[adj_idx], self.yCenters[adj_idx]]))
            candidate_segments.append((dist, adj, adj_idx))

        dist2, loc2, idx2 = min(candidate_segments, key=lambda x: x[0])
        return [(closest_dist, closest_loc, closest_idx), (dist2, loc2, idx2)]

    def cal_distance_location(self, location, xCenter, yCenter):
        # distance = abs(a*x1 + b*y1 + c)/(a^2+b^2)^(1/2)
        a = (self.yCenters[location - 1] - self.initCenter[1]) / (self.xCenters[location - 1] - self.initCenter[0])
        b = -1
        c = (self.yCenters[location - 1] - self.initCenter[1]) / (self.xCenters[location - 1] - self.initCenter[0]) * \
            self.initCenter[0] - self.initCenter[1]
        distance = abs(a * xCenter + b * yCenter + c) / (a ** 2 + b ** 2) ** (1 / 2)
        distance = round(distance, 6)
        return distance

    def estimate_weight(self, zCenter: float, i1: int, i2: int, ratio1: float, ratio2: float):
        ## y = ax // a = self.coefficient[i1], coefficient[i2]
        weights = []
        if zCenter > 0:

            loc1_weight = self.coefficient[i1]*zCenter

            loc2_weight = self.coefficient[i2]*zCenter
            threshold1 = self.zCenters[i1] / 5
            threshold15 = threshold1 * 1.5
            threshold2 = self.zCenters[i2] / 5
            threshold25 = threshold2 * 1.5
            if zCenter <= threshold1:
                coeff1 = 1.4
            elif threshold1 < zCenter <= threshold15:
                coeff1 = 1.2
            else:
                coeff1 = 1.0

            if zCenter <= threshold2:
                coeff2 = 1.4
            elif threshold2 < zCenter <= threshold25:
                coeff2 = 1.2
            else:
                coeff2 = 1.0

            weights.append(coeff1*loc1_weight*ratio2)
            weights.append(coeff2*loc2_weight*ratio1)
            # print(f"wewight:{int(sum(weights))}, nrw1: {coeff1 * loc1_weight}, nrw2: {coeff2 * loc2_weight}, weigh1: {coeff1 * loc1_weight * ratio2}, weigh2: {coeff2 * loc2_weight * ratio1}, coeff1: {coeff1}, coeff2: {coeff2}, int1: {i1}, int2: {i2}, coefficient[i1]: {self.coefficient[i1]}, coefficient[i2]: {self.coefficient[i2]}, zcenter: {zCenter}, ratio1: {ratio1}, ratio2: {ratio2}")
        return int(sum(weights)) if weights else 0

    def estimate_location_weight(self, xCenter: float, yCenter: float, zCenter: float) -> (int, float):
        locations = self.estimate_location(xCenter, yCenter)
        (dist1, loc1, idx1), (dist2, loc2, idx2) = locations

        distance1 = self.cal_distance_location(loc1, xCenter, yCenter)
        distance2 = self.cal_distance_location(loc2, xCenter, yCenter)

        total_dist = distance1 + distance2
        if total_dist == 0:
            ratio1 = ratio2 = 0.5
        else:
            ratio1 = distance2 / total_dist
            ratio2 = distance1 / total_dist

        weight = self.estimate_weight(zCenter, idx1, idx2, ratio1, ratio2)
        # print(f"weight: {weight}, loc1: {loc1}, loc2: {loc2}, d1: {distance1}, d2: {distance2}, ratio1: {ratio1}, ratio2: {ratio2}")

        combined_loc = int(f"{loc1}{loc2}")
        return combined_loc, weight