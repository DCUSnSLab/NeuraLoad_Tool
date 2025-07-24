import os
import sys
import time
import numpy as np
from typing import List
from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SensorFrame, SENSORLOCATION, AlgorithmData
from Algorithm.RefValueGenerator_COG import COGRefValGenerator

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)

from AlgorithmInterface import AlgorithmBase
from Algorithm.cog_estimation import init_sensor_values, process_sensor_data, estimate_cog_position_weight


class COGPottingMassEstimation_v6(AlgorithmBase):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            description="C 확장 모듈 기반 COG 위치 및 무게 추정 알고리즘",
            refValGen=COGRefValGenerator()
        )
        self.window_size = 30
        self.buffer_counts = [0] * 4
        self.buffer_index = 0
        self.value_buffer = [[0.0] * self.window_size for _ in range(4)]
        self.sensorWeights = np.array([1.0, 0.45, 1.0, 0.45], dtype=np.double)
        self.deltas = {i: [] for i in range(4)}
        self.init_values = None
        self.samples_buffer = []

    def initAlgorithm(self):
        print('init Algorithm ->', self.name)

    def runAlgo(self, algo_data: AlgorithmData) -> AlgorithmData:
        try:
            frame: SensorFrame = self.input_data
            laser_values = [
                frame.get_sensor_data(SENSORLOCATION.get_sensor_location(i)).distance
                for i in range(4)
            ]

            if self.init_values is None:
                self.samples_buffer.append(laser_values)
                if len(self.samples_buffer) >= 50:
                    samples = np.array(self.samples_buffer, dtype=np.double)
                    self.init_values = init_sensor_values(samples)
                    self.samples_buffer = []

            if self.init_values is None:
                algo_data.error = 1
                return algo_data

            deltas, self.buffer_index = process_sensor_data(
                laser_values,
                self.init_values,
                self.buffer_counts,
                self.buffer_index,
                self.value_buffer
            )

            filtered_deltas = np.array(deltas, dtype=np.double) * self.sensorWeights
            for idx, change in enumerate(filtered_deltas):
                self.deltas[idx] = [change]

            location, weight = estimate_cog_position_weight(filtered_deltas.tolist())
            algo_data.algo_type = ALGORITHM_TYPE.COGPottingMassEstimation_v6
            algo_data.position = location
            algo_data.predicted_weight = weight
            algo_data.error = 0

            return algo_data

        except Exception as e:
            print(f"Algorithm error in {self.name}: {str(e)}")
            algo_data.error = 1
            return algo_data
