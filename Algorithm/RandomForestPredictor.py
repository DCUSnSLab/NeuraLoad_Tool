import os
import sys
import json
import time
import numpy as np
import joblib
from typing import Dict, List, Any, Optional

# 상위 디렉토리의 모듈을 import 하기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from AlgorithmInterface import AlgorithmBase


class RandomForestPredictor(AlgorithmBase):
    """
    RandomForest 모델을 사용한 무게 및 위치 예측 알고리즘

    4개의 레이저 센서 데이터를 입력받아 무게와 위치를 예측합니다.
    """

    def __init__(self, model_path=None):
        """
        알고리즘 초기화

        Args:
            model_path: RandomForest 모델 파일 경로
        """
        super().__init__(
            name="RandomForestPredictor",
            description="랜덤 포레스트 모델을 사용한 무게 및 위치 예측 알고리즘"
        )

        # 모델 파일 경로
        self.model_path = model_path

        # 모델 로드
        try:
            self.model = self._load_model()
        except Exception as e:
            self.model = None

    def _load_model(self):
        """모델 파일 로드"""
        # 모델 파일 상대 경로 처리
        if not os.path.isabs(self.model_path):
            self.model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.model_path)

        # 모델 로드
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        else:
            raise FileNotFoundError(f"모델 파일이 존재하지 않습니다: {self.model_path}")

    def preprocess_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 데이터 전처리

        Args:
            data: 전처리할 원시 데이터
                - laser_values: 레이저 센서 값 리스트 (4개 실수)
                또는
                - laser1, laser2, laser3, laser4: 개별 레이저 센서 값

                모델 추론에 필요한 입력을 해당 함수에서 생성(불필요한 경우 미작성)
        Returns:
            전처리된 데이터
        """
        # 모델 검증
        if self.model is None:
            return {'error': "모델이 로드되지 않았습니다"}

        # 입력 데이터 추출
        laser_values = []

        # 리스트 형태로 입력된 경우
        if 'laser_values' in data and isinstance(data['laser_values'], list):
            laser_values = data['laser_values']

        # 개별 값으로 입력된 경우
        elif all(f'laser{i}' in data for i in range(1, 5)):
            for i in range(1, 5):
                try:
                    laser_values.append(float(data[f'laser{i}']))
                except (ValueError, TypeError):
                    laser_values.append(0.0)

        # 입력 데이터가 없는 경우
        else:
            return {'error': "유효한 레이저 센서 값이 입력되지 않았습니다"}

        # 전처리 결과 반환
        return {
            'processed_values': np.array([laser_values])
        }

    def process(self) -> Dict[str, Any]:
        """
        알고리즘 주요 처리 로직

        해당 함수에서 본인이 학습시킨 모델을 추론하기 위한 과정 수행

        Returns:
            처리 결과
        """
        # 전처리된 데이터 확인
        if 'error' in self.input_data:
            return self.input_data

        if 'processed_values' not in self.input_data:
            return {'error': '유효한 입력 데이터가 없습니다'}

        # 입력 데이터 추출
        processed_values = self.input_data['processed_values']

        try:
            # 모델 예측 수행
            predictions = self.model.predict(processed_values)

            # 예측 결과 파싱
            predicted_weights = predictions[:, 0]  # 첫 번째 열: 무게
            predicted_positions = predictions[:, 1]  # 두 번째 열: 위치

            # 위치는 정수형으로 반올림
            predicted_positions_rounded = np.rint(predicted_positions).astype(int)

            # 결과 처리
            return {
                'weight': float(predicted_weights[0]),
                'position': int(predicted_positions_rounded[0]),
                'raw_predictions': predictions.tolist(),
                'input_values': processed_values.tolist()
            }

        except Exception as e:
            return {'error': f"모델 예측 중 오류 발생: {str(e)}"}

    def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        알고리즘 실행 (오버라이드)

        Args:
            input_data: 입력 데이터

        Returns:
            알고리즘 실행 결과
        """
        try:
            self.is_running = True

            start_time = time.time()

            # 입력 데이터가 제공되면 설정
            if input_data is not None:
                # 전처리
                self.input_data = self.preprocess_data(input_data)  # 여기서 바로 설정

            # 입력 데이터 검증
            if not self.input_data or 'error' in self.input_data:
                return self.input_data or {'error': '유효한 입력 데이터가 없습니다'}

            # 알고리즘 처리
            results = self.process()

            # 출력 데이터 설정
            self.output_data = results

            self.execution_time = time.time() - start_time

            # 실행 이력 업데이트
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


# 테스트 코드
if __name__ == "__main__":
    # 임시 모델 저장
    model_path = "../GPT_new_best_regression_model.joblib"

    # 알고리즘 인스턴스 생성 (임시 모델 사용)
    predictor = RandomForestPredictor(model_path=model_path)

    # 테스트 데이터
    test_data = [613, 649, 606, 673]

    # execute 메서드 사용
    result = predictor.execute({'laser_values': test_data})

    print(f"입력값: {test_data}")
    print(f"예측 무게: {result.get('weight')} kg")
    print(f"예측 위치: {result.get('position')}")

    print(predictor.get_output_data())
    print(predictor.get_history())