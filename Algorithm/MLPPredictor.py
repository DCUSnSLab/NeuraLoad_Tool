import os
import sys
import time
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

    def preprocess_data(self, data: Union[list, dict]) -> Dict[str, Any]:
        if self.model is None or self.scaler is None:
            return {'error': "모델 또는 스케일러가 로드되지 않았습니다."}

        sensor_values = []

        # 직접 리스트로 받은 경우
        if isinstance(data, list) and len(data) == 4:
            try:
                sensor_values = [float(x) for x in data]
            except Exception:
                return {'error': '센서 값 형식 오류'}
        # JSON 형태(dict)인 경우도 여전히 지원
        elif isinstance(data, dict) and all(k in data for k in ['A', 'B', 'C', 'D']):
            try:
                sensor_values = [float(data[k]) for k in ['A', 'B', 'C', 'D']]
            except Exception:
                return {'error': '센서 값 형식 오류'}
        else:
            return {'error': '유효한 센서 입력이 없습니다'}

        input_array = np.array([sensor_values])
        scaled_input = self.scaler.transform(input_array)

        return {'processed_values': scaled_input}

    def process(self) -> Dict[str, Any]:
        if 'error' in self.input_data:
            return self.input_data
        if 'processed_values' not in self.input_data:
            return {'error': '입력 데이터가 누락되었습니다'}

        try:
            prediction = self.model.predict(self.input_data['processed_values'], verbose=0)[0]
            weight = float(prediction[0])
            position = int(np.rint(prediction[1]))

            return {
                'weight': weight,
                'position': position,
                'raw_predictions': prediction.tolist(),
                'input_values': self.input_data['processed_values'].tolist()
            }
        except Exception as e:
            return {'error': f"모델 예측 중 오류: {e}"}

    def execute(self, input_data: Optional[Union[list, dict]] = None) -> Dict[str, Any]:
        try:
            self.is_running = True
            start_time = time.time()

            if input_data is not None:
                self.input_data = self.preprocess_data(input_data)

            if not self.input_data or 'error' in self.input_data:
                return self.input_data or {'error': '입력 오류'}

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

    # 센서에서 직접 수신한 형태 (예: list로 들어오는 경우)
    test_input = [2, 6, 76, -33]

    result = predictor.execute(test_input)

    print(f"\n입력값: {test_input}")
    if result.get("weight") is not None and result.get("position") is not None:
        print(f"예측 무게: {result.get('weight'):.2f} kg")
        print(f"예측 위치: {result.get('position')}")
    else:
        print(f"예측 실패: {result.get('error')}")