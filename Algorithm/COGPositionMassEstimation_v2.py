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


class COGPositionMassEstimation_v2(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="레이저 센서 변화량 기반 roll, pitch로 추정한 COG 좌표로 적재위치 및 무게 추정 알고리즘"
        )
        self.initCenter = np.array([815, 1430, 0])  # 초기 중심 좌표
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
        self.xCenters = np.array([794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959, 834.6214622])
        self.yCenters = np.array([1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957, 1447.492051])
        self.zCenters = np.array([13.9859375, 15.51666667, 14.2640625, 16.65625, 16.3, 15.884375, 15.31041667, 17.61875, 15.29375])
        #
        # self.sensorWeights = np.array([1.0, 1.0, 1.0, 1.0])  # 전방 센서 1.0, 후방 센서 1.0
        # # 가중치 전방센서(1), 후방센서(1)
        # self.xCenters = np.array([784.1399539, 813.0808429, 842.0217319, 784.1430245, 813.7425683, 843.342112, 784.1460952, 814.4042936, 844.6624921])
        # self.yCenters = np.array([1428.934278, 1427.761984, 1426.58969, 1453.964536, 1453.456541, 1452.948547, 1478.994793, 1479.151099, 1479.307405])
        # self.zCenters = np.array([18.78125, 18.47395833, 18.16666667, 23.90729167, 23.7609375, 23.61458333, 29.03333333, 29.04791667, 29.0625])
        #


    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self, algo_data:AlgorithmData) -> AlgorithmData:
        print("inprocess")
        deltas = self.preprocess_data(algo_data.referenceValue)
        xCenter, yCenter, zCenter = self.calculate_cog(deltas)
        location, weight = self.estimate_location_weight(xCenter, yCenter, zCenter)

        algo_data.algo_type=ALGORITHM_TYPE.COGPositionMassEstimation_v2
        algo_data.position = location
        algo_data.predicted_weight=weight
        algo_data.error=0
        return algo_data

    def preprocess_data(self, input_data):
        weighted_deltas = input_data * self.sensorWeights
        return weighted_deltas

    def calculate_cog(self, deltas: np.ndarray) -> (float, float, float):
        roll = ((deltas[0] - deltas[2]) + (deltas[1] - deltas[3])) / (((self.sensorCoords[3, 0] - self.sensorCoords[1, 0]) + (self.sensorCoords[2, 0] - self.sensorCoords[0, 0])) / 2)
        pitch = ((deltas[0] - deltas[1]) + (deltas[2] - deltas[3])) / (((self.sensorCoords[3, 1] - self.sensorCoords[2, 1]) + (self.sensorCoords[1, 1] - self.sensorCoords[0, 1])) / 2)
        x_center = (self.loadingBoxWidth / 2) - roll * (self.loadingBoxWidth / 2)
        y_center = (self.loadingBoxLength / 2) - pitch * (self.loadingBoxLength / 2)
        z_center = (deltas[0] + deltas[1] + deltas[2] + deltas[3]) / 4
        return x_center, y_center, z_center

    def estimate_location_weight(self, xCenter: float, yCenter: float, zCenter: float) -> (int, float):
        results = []
        current = np.array([xCenter, yCenter, zCenter])
        for i, location in enumerate(self.locations):
            base = np.array([self.xCenters[i], self.yCenters[i], self.zCenters[i]])
            direction = base - self.initCenter
            if np.linalg.norm(direction) == 0:
                continue
            to_target = current - self.initCenter
            projection_length = np.dot(to_target, direction) / np.linalg.norm(direction)
            if projection_length <= 0:
                continue
            scale = projection_length / np.linalg.norm(direction)
            weight = scale * 500  # max weight 기준
            direction_unit = direction / np.linalg.norm(direction)
            proj_vec = projection_length * direction_unit
            orth_dist = np.linalg.norm(to_target - proj_vec)
            results.append((location, weight, orth_dist))

        if not results:
            print(f"[WARNING] estimate_location_weight: No valid projections for ({xCenter:.2f}, {yCenter:.2f}, {zCenter:.2f})")
            return -1, -1.0

        location, weight, _ = min(results, key=lambda x: x[2])
        return location, int(weight)
