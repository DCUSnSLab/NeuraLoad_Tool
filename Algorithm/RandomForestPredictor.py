import os
import sys
import json
import time
import numpy as np
import joblib
import datetime
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

    def __init__(self, name):
        """
        알고리즘 초기화

        Args:
            model_path: RandomForest 모델 파일 경로
        """
        super().__init__(
            name=name,
            description="랜덤 포레스트 모델을 사용한 무게 및 위치 예측 알고리즘",
            model_path="../model/best_regression_model.joblib"
        )

        '''
        입력 센서 데이터 구조
        {'VCOM3': {'timestamp': '17_40_42_396', 'value': 422, 'sub1': 460, 'sub2': 464, 'Data_port_number': 'VCOM3',
                   'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 396000)},
         'VCOM4': {'timestamp': '17_40_42_397', 'value': 455, 'sub1': 455, 'sub2': 479, 'Data_port_number': 'VCOM4',
                   'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 397000)},
         'VCOM1': {'timestamp': '17_40_42_399', 'value': 406, 'sub1': 405, 'sub2': 409, 'Data_port_number': 'VCOM1',
                   'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 399000)},
         'VCOM2': {'timestamp': '17_40_42_400', 'value': 455, 'sub1': 443, 'sub2': 420, 'Data_port_number': 'VCOM2',
                   'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 400000)}}
        '''

        self.input_data.append("value")

        # 모델 로드
        try:
            self.model = self._load_model()
        except Exception as e:
            print(e)
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

    def runAlgo(self) -> Dict[str, Any]:
        """
        알고리즘 주요 처리 로직

        해당 함수에서 본인이 학습시킨 모델을 추론하기 위한 과정 수행

        Returns:
            처리 결과
        """

        try:
            # 모델 예측 수행
            predictions = self.model.predict([self.refined_data])
            #print(predictions)

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
                'input_values': self.refined_data
            }

        except Exception as e:
            return {'error': f"모델 예측 중 오류 발생: {str(e)}"}

    def initAlgorithm(self):
        pass#print('init Algorithm -> ',self.name)

    def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.data = input_data
        # 알고리즘 별 입력 데이터 정의에 따라 후처리 수행
        self.preprocessing()
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

            # 알고리즘 처리
            results = self.runAlgo()

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
    # 알고리즘 인스턴스 생성 (임시 모델 사용)
    predictor = RandomForestPredictor()
    # 테스트 데이터
    # test_data = [613, 649, 606, 673]
    new_test_data = {
        'VCOM3': {'timestamp': '17_40_42_396', 'value': 422, 'sub1': 460, 'sub2': 464, 'Data_port_number': 'VCOM3', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 396000)},
        'VCOM4': {'timestamp': '17_40_42_397', 'value': 455, 'sub1': 455, 'sub2': 479, 'Data_port_number': 'VCOM4', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 397000)},
        'VCOM1': {'timestamp': '17_40_42_399', 'value': 406, 'sub1': 405, 'sub2': 409, 'Data_port_number': 'VCOM1', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 399000)},
        'VCOM2': {'timestamp': '17_40_42_400', 'value': 455, 'sub1': 443, 'sub2': 420, 'Data_port_number': 'VCOM2', 'timestamp_dt': datetime.datetime(2025, 4, 6, 17, 40, 42, 400000)}
    }

    # execute 메서드 사용
    result = predictor.execute(new_test_data)

    #print(f"입력값: {new_test_data}")
    #print(f"예측 무게: {result.get('weight')} kg")
    #print(f"예측 위치: {result.get('position')}")

    #print(predictor.get_output_data())
    #print(predictor.get_history())