import os
import sys
import time
import numpy as np
import datetime
from typing import Dict, Any, Optional

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

#from tensorflow.keras.models import load_model
from joblib import load as joblib_load

# 상위 디렉토리 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from AlgorithmInterface import AlgorithmBase


class KerasMLPPredictor(AlgorithmBase):
    """
    Keras 기반 MLP 모델을 사용한 무게 및 위치 예측 알고리즘 (센서 변화량 기반)
    """

    def __init__(self, name):
        super().__init__(
            name=name,
            description="Keras 기반 MLP 모델을 사용한 무게 및 위치 예측 알고리즘 (센서 변화량 기반)",
            model_path="../model/mlp_20250403_135334_best.h5"
        )

        self.scaler_path = "../model/scaler_20250403_135334.save"
        self.input_data.append("value")

        # 센서 초기값 저장용
        self.initial_values = {}

    def initAlgorithm(self):
        # 모델 및 스케일러 로드
        model_abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.model_path)
        scaler_abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.scaler_path)

        try:
            #self.model = load_model(model_abspath, compile=False)
            self.scaler = joblib_load(scaler_abspath)
            # print("모델과 스케일러 로드 완료")
        except Exception as e:
            # print(f"모델 또는 스케일러 로드 실패: {e}")
            self.model = None
            self.scaler = None

    def runAlgo(self) -> Dict[str, Any]:
        try:
            if self.model is None or self.scaler is None:
                return {'error': "모델 또는 스케일러가 초기화되지 않았습니다."}

            # 현재 센서값 추출
            current_values = {
                "VCOM1": self.data["VCOM1"]["value"],
                "VCOM2": self.data["VCOM2"]["value"],
                "VCOM3": self.data["VCOM3"]["value"],
                "VCOM4": self.data["VCOM4"]["value"]
            }

            # 초기값 저장 (최초 실행 시에만)
            for key in current_values:
                if key not in self.initial_values:
                    self.initial_values[key] = current_values[key]

            # 변화량 계산
            delta_values = [
                current_values["VCOM1"] - self.initial_values["VCOM1"],
                current_values["VCOM2"] - self.initial_values["VCOM2"],
                current_values["VCOM3"] - self.initial_values["VCOM3"],
                current_values["VCOM4"] - self.initial_values["VCOM4"]
            ]

            # 스케일링 및 예측
            input_array = np.array(delta_values).reshape(1, -1)
            scaled_input = self.scaler.transform(input_array)
            predictions = self.model.predict(scaled_input, verbose=0)

            weight = float(predictions[0][0])
            position = int(round(predictions[0][1]))

            return {
                'weight': weight,
                'position': position,
                'raw_predictions': predictions.tolist(),
                'input_values': current_values,
                'delta_values': delta_values
            }

        except Exception as e:
            return {'error': f"모델 예측 중 오류 발생: {str(e)}"}

    def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.data = input_data
        self.preprocessing()

        try:
            self.is_running = True
            start_time = time.time()

            results = self.runAlgo()

            self.output_data = results
            self.execution_time = time.time() - start_time

            self.execution_history.append({
                'timestamp': time.time(),
                'input_keys': list(self.input_data.keys() if isinstance(self.input_data, dict) else []),
                'output_keys': list(self.output_data.keys() if isinstance(self.output_data, dict) else []),
                'execution_time': self.execution_time
            })

            return self.output_data

        except Exception as e:
            return {'error': f"알고리즘 실행 중 오류: {str(e)}"}
        finally:
            self.is_running = False

    def reset_initial_values(self):
        """초기 센서값 재설정"""
        self.initial_values = {}
        #print("🌀 초기 센서값이 리셋되었습니다.")


# 테스트 코드
if __name__ == "__main__":
    predictor = KerasMLPPredictor()

    test_data = {
        'VCOM3': {'timestamp': '17_40_42_396', 'value': 422, 'sub1': 460, 'sub2': 464, 'Data_port_number': 'VCOM3', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 396000)},
        'VCOM4': {'timestamp': '17_40_42_397', 'value': 455, 'sub1': 455, 'sub2': 479, 'Data_port_number': 'VCOM4', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 397000)},
        'VCOM1': {'timestamp': '17_40_42_399', 'value': 406, 'sub1': 405, 'sub2': 409, 'Data_port_number': 'VCOM1', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 399000)},
        'VCOM2': {'timestamp': '17_40_42_400', 'value': 455, 'sub1': 443, 'sub2': 420, 'Data_port_number': 'VCOM2', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 400000)}
    }

    result = predictor.execute(test_data)

    #print(f"입력값: {test_data}")
    #print(f"예측 무게: {result.get('weight')} kg")
    #print(f"예측 위치: {result.get('position')}")
    #print(f"변화량: {result.get('delta_values')}")
    #print(predictor.get_output_data())
    #print(predictor.get_history())