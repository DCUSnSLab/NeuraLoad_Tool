import os
import sys
import time
import numpy as np
import datetime
from typing import Dict, Any, Optional

# suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from tensorflow.keras.models import load_model
from joblib import load as joblib_load

# add parent directory to path for AlgorithmInterface
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from AlgorithmInterface import AlgorithmBase
from datainfo import SensorFrame, SensorData


class KerasMLPPredictor(AlgorithmBase):
    """
    Keras 기반 MLP 모델을 사용한 무게 및 위치 예측 알고리즘
    입력: SensorFrame 객체 (바이너리 데이터 파싱 후)
    출력: 무게(weight), 위치(position)
    """

    def __init__(self, name: str = "KerasMLPPredictor"):
        super().__init__(
            name=name,
            description="Keras 기반 MLP 모델을 사용한 무게 및 위치 예측 알고리즘 (센서 변화량 기반)",
            model_path=os.path.join(parent_dir, 'model', 'mlp_20250403_135334_best.h5')
        )
        # scaler 경로
        self.scaler_path = os.path.join(parent_dir, 'model', 'scaler_20250403_135334.save')
        # 초기 센서값 저장용
        self.initial_values: Dict[str, int] = {}

    def initAlgorithm(self):
        # 모델 및 스케일러 로드
        try:
            self.model = load_model(self.model_path, compile=False)
            self.scaler = joblib_load(self.scaler_path)
        except Exception as e:
            self.model = None
            self.scaler = None
            print(f"모델 또는 스케일러 로드 실패: {e}")

    def runAlgo(self, frame: SensorFrame) -> Dict[str, Any]:
        # 모델/스케일러 확인
        if self.model is None or self.scaler is None:
            return {'error': "모델 또는 스케일러가 초기화되지 않았습니다."}

        # SensorFrame에서 센서 리스트 추출 및 location 순서(0,1,2,3)로 정렬
        sensors = frame.get_sensors()
        sensors_sorted = sorted(sensors, key=lambda s: s.location.value)

        # 거리(distance) 값을 포트 기준으로 꺼내고 초기값 설정
        current_values = {}
        for sensor in sensors_sorted:
            port = sensor.serial_port
            val = sensor.distance
            current_values[port] = val
            if port not in self.initial_values:
                self.initial_values[port] = val

        # 변화량을 location 순서대로 계산
        delta_values = [current_values[sensor.serial_port] - self.initial_values[sensor.serial_port]
                        for sensor in sensors_sorted]

        # 입력 배열 생성 및 스케일링
        input_array = np.array(delta_values).reshape(1, -1)
        scaled_input = self.scaler.transform(input_array)

        # 예측 수행
        predictions = self.model.predict(scaled_input, verbose=0)
        weight = round(float(predictions[0][0]), 2)
        position = int(round(predictions[0][1]))

        return {
            'weight': weight,
            'position': position,
            'raw_predictions': predictions.tolist(),
            'input_distances': [sensor.distance for sensor in sensors_sorted],
            'delta_distances': delta_values
        }

    def execute(self, frame: SensorFrame) -> Dict[str, Any]:
        """
        SensorFrame을 받아 예측 결과 반환
        """
        # 알고리즘 초기화
        if not hasattr(self, 'model') or self.model is None:
            self.initAlgorithm()

        self.is_running = True
        start_time = time.time()
        try:
            results = self.runAlgo(frame)
            self.execution_time = time.time() - start_time
            # 실행 기록 저장 (location 순서 반영)
            self.execution_history.append({
                'timestamp': time.time(),
                'execution_time': self.execution_time,
                'sensor_order': [sensor.location.name for sensor in sorted(frame.get_sensors(), key=lambda s: s.location.value)],
                'output_keys': list(results.keys())
            })
            return results
        except Exception as e:
            return {'error': f"알고리즘 실행 중 오류: {e}"}
        finally:
            self.is_running = False

    def reset_initial_values(self):
        """초기 센서값 재설정"""
        self.initial_values.clear()
        print("초기 센서값이 리셋되었습니다.")