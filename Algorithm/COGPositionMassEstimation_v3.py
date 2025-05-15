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

        self.initial_laser_values = None

        self.locations = np.arange(1, 10)
        # 가중치 전방센서(1), 후방센서(0.45)
        self.initCenter = np.array([815, 1430, 0])
        # self.sensorWeights = np.array([1.0, 0.45, 1.0, 0.45])
        # self.xCenters = np.array([794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959, 834.6214622])
        # self.yCenters = np.array([1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957, 1447.492051])
        # self.zCenters = np.array([13.9859375, 15.51666667, 14.2640625, 16.65625, 16.3, 15.884375, 15.31041667, 17.61875, 15.29375])
        self.sensorWeights = np.array([1.0, 1.0, 1.0, 1.0])
        self.xCenters = np.array([787.0877792,  814.8771739,  839.9643955,  782.7581608,  811.1309793,  837.1086898,  785.3743557,  812.6048919,  843.4710794])
        self.yCenters = np.array([1426.94493,  1429.336884,  1426.518641,  1456.003617,  1451.456536,  1453.019595,  1479.942102,  1481.01256,  1479.430555])
        self.zCenters = np.array([18.78125,  21.29166667,  19.09375,  27.3125,  26.0625,  25.75,  29.45,  32.8125,  29.34166667])
        self.deltas = {i: [] for i in range(4)}
        self.alpha = 0.2
        self.previous_values = None
    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self, algo_data: AlgorithmData) -> AlgorithmData:
        deltas = self.preprocess_data(self.input_data, algo_data.referenceValue)
        xCenter, yCenter, zCenter = self.calculate_cog(deltas)
        location, weight = self.estimate_location_weight(xCenter, yCenter, zCenter)
        algo_data.algo_type = ALGORITHM_TYPE.COGPositionMassEstimation_v3
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
            laser_values = [0,0,0,0]
            for i in range(4):
                laser_values[i] = frame.get_sensor_data(SENSORLOCATION.get_sensor_location(i)).distance
            # laser_values = [
            #     frame.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance, # 2번
            #     frame.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance, # 4번
            #     frame.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance, # 3번
            #     frame.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance, # 1번
            # ]
            # print('------------------------------------------------------')
            # print("laser_values:", laser_values)
            # print(frame.get_sensor_data(SENSORLOCATION.TOP_LEFT))
            # print(frame.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT))
            # print(frame.get_sensor_data(SENSORLOCATION.TOP_RIGHT))
            # print(frame.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT))
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

    def estimate_location(self, xCenter: float, yCenter: float):
        if xCenter == self.xCenters[4] and yCenter == self.yCenters[4]:  # 5번 위치일 경우
            return [(0, 5, 4)]  # 5번 위치를 바로 반환

        distances = []
        for i, location in enumerate(self.locations):
            if location == 5:  # 5번 위치는 제외
                continue
            x, y = self.xCenters[i], self.yCenters[i]
            dist = ((x - xCenter) ** 2 + (y - yCenter) ** 2) ** 0.5
            distances.append((dist, location, i))
        distances.sort(key=lambda x: x[0])
        return distances[:2]

    def estimate_weight(self, zCenter: float, i1: int, i2: int, ratio1: float, ratio2: float):
        dz = zCenter - self.initCenter[2]
        direction_z1 = self.zCenters[i1] - self.initCenter[2]
        direction_z2 = self.zCenters[i2] - self.initCenter[2]
        weights = []
        if direction_z1 != 0:
            scale1 = dz / direction_z1
            if scale1 > 0:
                weights.append(ratio2 * scale1 * 500)
        if direction_z2 != 0:
            scale2 = dz / direction_z2
            if scale2 > 0:
                weights.append(ratio1 * scale2 * 500)
        # print(f"zCenter: {zCenter}, zCenter-zMin: {dz} l1_zMax-zMin: {direction_z1}, l2_zMax-zMin: {direction_z2} ||| location1: {i1+1},scale1: {scale1}, ratio1: {ratio1}, scale1_w: {scale1*500} ||| location2: {i2+1}, scale2: {scale2}, scale2_w: {scale2*500}, ratio2: {ratio2} ||| weight: {weights}, total_weight: {sum(weights)}")
        return sum(weights) if weights else 0

    def estimate_location_weight(self, xCenter: float, yCenter: float, zCenter: float) -> (int, float):
        locations = self.estimate_location(xCenter, yCenter)
        (d1, loc1, i1), (d2, loc2, i2) = locations
        total_dist = d1 + d2

        if total_dist == 0:
            ratio1 = ratio2 = 0.5
        else:
            ratio1 = d1 / total_dist
            ratio2 = d2 / total_dist

        weight = self.estimate_weight(zCenter, i1, i2, ratio1, ratio2)
        return loc1, int(weight)
