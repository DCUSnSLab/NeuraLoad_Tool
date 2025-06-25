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
from Algorithm.Location_data import LOCATION_CONSTANTS, WEIGHT

# 상위 디렉토리의 모듈을 import 하기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import datetime
from AlgorithmInterface import AlgorithmBase  # 상속용 추상 클래스


class COGPositionMassEstimation_v5(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="레이저 센서 변화량 기반 roll, pitch로 추정한 COG 좌표로 적재위치 및 무게 추정 알고리즘",
            refValGen=COGRefValGenerator()
        )

        self.loadingBoxWidth = 1630
        self.loadingBoxLength = 2860
        self.sensorCoords = np.array([
            [373.1, 1],  # TL (Top Left)
            [201, 2516.9],  # BL (Bottom Left)
            [1256.9, 1],  # TR (Top Right)
            [1429, 2516.9]  # BR (Bottom Right)
        ])
        self.constants = LOCATION_CONSTANTS
        self.weight_bins = WEIGHT
        self.initial_laser_values = None

        self.locations = np.arange(1, 10)
        # 가중치 전방센서(1), 후방센서(0.45)
        self.sensorWeights = np.array([1.0, 0.45, 1.0, 0.45])
        self.initCenter = np.array([815, 1430])
        self.xCenters = np.array(
            [794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959,
             834.6214622])
        self.yCenters = np.array(
            [1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957,
             1447.492051])

        self.deltas = {i: [] for i in range(4)}
        self.window_size = 15
        self.value_buffer = None

    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def apply_moving_average_filter(self, current_values: List[float]) -> List[float]:
        if self.value_buffer is None:
            self.value_buffer = [deque([v], maxlen=self.window_size) for v in current_values]
            return current_values

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
            laser_values = [0, 0, 0, 0]
            for i in range(4):
                laser_values[i] = frame.get_sensor_data(SENSORLOCATION.get_sensor_location(i)).distance
        except Exception as e:
            return {'error': f'센서 데이터 추출 오류: {str(e)}'}

        deltas = self.compute_deltas(laser_values, init_value)
        filtered_deltas = self.apply_moving_average_filter(deltas)
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
        deltas = np.array(deltas) * self.sensorWeights
        roll = ((deltas[0] - deltas[2]) + (deltas[1] - deltas[3])) / (((self.sensorCoords[3, 0] - self.sensorCoords[
            1, 0]) + (self.sensorCoords[2, 0] - self.sensorCoords[0, 0])) / 2)
        pitch = ((deltas[0] - deltas[1]) + (deltas[2] - deltas[3])) / (((self.sensorCoords[3, 1] - self.sensorCoords[
            2, 1]) + (self.sensorCoords[1, 1] - self.sensorCoords[0, 1])) / 2)
        x_center = (self.loadingBoxWidth / 2) - roll * (self.loadingBoxWidth / 2)
        y_center = (self.loadingBoxLength / 2) - pitch * (self.loadingBoxLength / 2)
        return x_center, y_center

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
        return [closest_loc, loc2]

    def cal_distance_location(self, location, xCenter, yCenter):
        # distance = abs(a*x1 + b*y1 + c)/(a^2+b^2)^(1/2)
        a = (self.yCenters[location - 1] - self.initCenter[1]) / (self.xCenters[location - 1] - self.initCenter[0])
        b = -1
        c = (self.yCenters[location - 1] - self.initCenter[1]) / (self.xCenters[location - 1] - self.initCenter[0]) * \
            self.initCenter[0] - self.initCenter[1]
        distance = abs(a * xCenter + b * yCenter + c) / (a ** 2 + b ** 2) ** (1 / 2)
        print("distance: ", distance)
        return distance

    def calculate_weight_estimation(self, location, deltas):
        top_left = deltas[0][0] if isinstance(deltas[0], list) else deltas[0]
        bottom_left = deltas[1][0] if isinstance(deltas[1], list) else deltas[1]
        top_right = deltas[2][0] if isinstance(deltas[2], list) else deltas[2]
        bottom_right = deltas[3][0] if isinstance(deltas[3], list) else deltas[3]

        mapping = {
            1: top_left,
            2: (top_left + top_right) / 2,
            3: top_right,
            4: (top_left + bottom_left) / 2,
            5: (top_left + bottom_left + top_right + bottom_right) / 4,
            6: (top_right + bottom_right) / 2,
            7: bottom_left,
            8: (bottom_left + bottom_right) / 2,
            9: bottom_right
        }

        if location in self.constants and location in mapping:
            avg = mapping[location]
            coarse = self.constants[location]

            for i in range(len(coarse) - 1):
                if coarse[i] <= avg <= coarse[i + 1]:
                    w1 = self.weight_bins[i]
                    w2 = self.weight_bins[i + 1]
                    fraction = (avg - coarse[i]) / (coarse[i + 1] - coarse[i])
                    interpolated_weight = w1 + fraction * (w2 - w1)
                    # print(f"{location} {avg:.4f} {coarse[i]} {coarse[i + 1]} {w1} {w2} {interpolated_weight:.2f}")
                    return interpolated_weight

            return self.weight_bins[0] if avg < coarse[0] else self.weight_bins[-1]

        return None

    def estimate_location_weight(self, xCenter: float, yCenter: float) -> (int, float):
        locations = self.estimate_location(xCenter, yCenter)
        if len(locations) < 2:
            loc1 = locations[0]
            weight_idx = self.calculate_weight_estimation(loc1, self.deltas)
            return int(str(loc1) + str(loc1)), weight_idx if weight_idx is not None else 0

        loc1, loc2 = locations
        distance1 = self.cal_distance_location(loc1, xCenter, yCenter)
        distance2 = self.cal_distance_location(loc2, xCenter, yCenter)

        total_dist = distance1 + distance2

        if total_dist == 0:
            ratio1 = ratio2 = 0.5
        else:
            ratio1 = distance2 / total_dist
            ratio2 = distance1 / total_dist

        w1 = self.calculate_weight_estimation(loc1, self.deltas)
        w2 = self.calculate_weight_estimation(loc2, self.deltas)

        estimated_weight = int(ratio1 * w1 + ratio2 * w2)
        print("loc1: ", loc1, "loc2 : ", loc2, "weight1: ", w1, ", weight2 :", w2, "ratio1: ", ratio1, "ratio2: ",
              ratio2, ", estimation_weight : ", estimated_weight)
        return int(str(loc1) + str(loc2)), estimated_weight

    def runAlgo(self, algo_data: AlgorithmData) -> AlgorithmData:
        deltas = self.preprocess_data(self.input_data, algo_data.referenceValue)
        xCenter, yCenter = self.calculate_cog(deltas)
        location, weight = self.estimate_location_weight(xCenter, yCenter)
        algo_data.algo_type = ALGORITHM_TYPE.COGPositionMassEstimation_v3
        algo_data.position = location
        algo_data.predicted_weight = weight
        algo_data.error = 0
        return algo_data