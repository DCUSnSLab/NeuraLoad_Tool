import os
import sys
import time
import datetime
import numpy as np
import joblib
from typing import Union, Dict, Any, Optional
from tensorflow.keras.models import load_model

# 상위 폴더 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from AlgorithmInterface import AlgorithmBase


class MLPPredictor(AlgorithmBase):
    def __init__(self):
        super().__init__(
            name="MLPPredictor",
            description="MLP 모델을 사용한 무게 및 위치 예측 알고리즘",
            model_path="../model/mlp_20250403_135334_best.h5"
        )
        self.scaler_path = "../model/scaler_20250403_135334.save"

        self.input_data.append("value")

        try:
            self.model = self._load_model()
            self.scaler = self._load_scaler()
        except Exception as e:
            print(f"모델 또는 스케일러 로드 오류: {e}")
            self.model = None
            self.scaler = None

    def _load_model(self):
        path = os.path.join(current_dir, self.model_path) if not os.path.isabs(self.model_path) else self.model_path
        if os.path.exists(path):
            return load_model(path, compile=False)
        else:
            raise FileNotFoundError(f"모델 파일 없음: {path}")

    def _load_scaler(self):
        path = os.path.join(current_dir, self.scaler_path) if not os.path.isabs(self.scaler_path) else self.scaler_path
        if os.path.exists(path):
            return joblib.load(path)
        else:
            print("scaler error")
            raise FileNotFoundError(f"스케일러 파일 없음: {path}")

    def process(self) -> Dict[str, Any]:

        try:
            # prediction = self.model.predict(self.input_data['processed_values'], verbose=0)[0]
            input_array = np.array([self.refined_data])
            scaled_input = self.scaler.transform(input_array)
            prediction = self.model.predict(scaled_input, verbose=0)[0]
            weight = float(prediction[0])
            position = int(np.rint(prediction[1]))

            return {
                'weight': weight,
                'position': position,
                'raw_predictions': prediction.tolist(),
                'input_values': self.refined_data
            }
        except Exception as e:
            return {'error': f"모델 예측 중 오류: {e}"}

    def execute(self, input_data: Optional[Union[list, dict]] = None) -> Dict[str, Any]:
        self.data = input_data
        # 알고리즘 별 입력 데이터 정의에 따라 후처리 수행
        self.preprocessing()
        try:
            self.is_running = True
            start_time = time.time()

            result = self.process()
            self.output_data = result

            self.execution_time = time.time() - start_time

            self.execution_history.append({
                'timestamp': time.time(),
                'input_keys': list(range(len(input_data))) if isinstance(input_data, list) else list(input_data.keys()),
                'output_keys': list(self.output_data.keys()),
                'execution_time': self.execution_time
            })

            return self.output_data
        except Exception as e:
            return {'error': f"알고리즘 실행 오류: {e}"}
        finally:
            self.is_running = False


# 테스트 코드
if __name__ == "__main__":
    predictor = MLPPredictor()

    new_test_data = {
        'VCOM3': {'timestamp': '17_40_42_396', 'value': 422, 'sub1': 460, 'sub2': 464, 'Data_port_number': 'VCOM3',
                  'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 396000)},
        'VCOM4': {'timestamp': '17_40_42_397', 'value': 455, 'sub1': 455, 'sub2': 479, 'Data_port_number': 'VCOM4',
                  'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 397000)},
        'VCOM1': {'timestamp': '17_40_42_399', 'value': 406, 'sub1': 405, 'sub2': 409, 'Data_port_number': 'VCOM1',
                  'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 399000)},
        'VCOM2': {'timestamp': '17_40_42_400', 'value': 455, 'sub1': 443, 'sub2': 420, 'Data_port_number': 'VCOM2',
                  'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 400000)}
    }

    # 센서에서 직접 수신한 형태 (예: list로 들어오는 경우)
    test_input = [2, 6, 76, -33]

    result = predictor.execute(new_test_data)