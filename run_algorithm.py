#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import importlib.util
import json
import time

def run_algorithm(file_path, sensor_data):
    """
    알고리즘 파일을 로드하고 실행하는 함수
    
    Args:
        file_path: 알고리즘 파일 경로
        sensor_data: 센서 데이터 (latest_candidate_window) JSON 문자열
    
    Returns:
        결과를 JSON 형식으로 반환
    """
    try:
        # 파일명 추출 (확장자 제외)
        file_name = os.path.basename(file_path)
        module_name = os.path.splitext(file_name)[0]
        
        # 모듈 동적 로딩
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            return json.dumps({"error": f"Module spec not found for {file_path}"})
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # 클래스 이름 찾기 - 파일명과 동일한 클래스 또는 첫 번째 AlgorithmBase 상속 클래스
        class_name = module_name
        
        # 클래스 객체 찾기
        algorithm_class = None
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and name == class_name:
                algorithm_class = obj
                break
                
        # 파일명과 일치하는 클래스가 없으면 AlgorithmBase 상속 클래스 찾기
        if algorithm_class is None:
            from AlgorithmInterface import AlgorithmBase
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, AlgorithmBase) and obj != AlgorithmBase:
                    algorithm_class = obj
                    break
        
        if algorithm_class is None:
            return json.dumps({"error": f"Algorithm class not found in {file_path}"})
        
        # 알고리즘 인스턴스 생성 및 실행
        algorithm_instance = algorithm_class()
        
        # JSON 문자열을 Python 객체로 변환
        sensor_data_dict = json.loads(sensor_data)
        
        # execute() 함수를 호출하여 처리
        result = algorithm_instance.execute(sensor_data_dict)
        
        # 결과 반환
        return json.dumps(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return json.dumps({"error": str(e), "traceback": error_trace})

if __name__ == "__main__":
    # 커맨드 라인 인자 처리
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: run_algorithm.py <algorithm_file_path> <sensor_data_json>"}))
        sys.exit(1)
    
    file_path = sys.argv[1]
    sensor_data = sys.argv[2]
    
    # 알고리즘 실행 및 결과 출력
    result = run_algorithm(file_path, sensor_data)
