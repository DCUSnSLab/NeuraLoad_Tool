from abc import ABC, abstractmethod
import logging
import os
import time
from typing import Dict, List, Any, Optional
from time import sleep

from datainfo import SensorFrame
from procImpl import processImpl


class AlgorithmBase(processImpl):
    """
    화물과적 중심 탄소중립을 위한 데이터 수집 툴 알고리즘 추상 클래스

    모든 알고리즘은 이 클래스를 상속받아 구현해야 함
    표준화된 인터페이스를 통해 다양한 입력/출력 데이터 처리
    """

    def __init__(self, name: str, description: str = "", model_path: str = ""):
        super().__init__(name)
        """
        알고리즘 클래스 초기화

        Args:
            name: 알고리즘 이름
            description: 알고리즘 설명
        """
        self.name = name
        self.description = description
        self.model_path = model_path
        self.input_data = []
        self.output_data = {'input':None, 'output':None}
        self.execution_time = 0
        self.is_running = False
        self.execution_history = []

    @abstractmethod
    def runAlgo(self) -> Dict[str, Any]:
        """
        알고리즘 주요 처리 로직

        Returns:
            처리 결과
        """
        pass

    def set_input_data(self, data: Optional[SensorFrame]) -> None:
        """
        알고리즘 입력 데이터 설정

        Args:
            data: 입력 데이터
        """
        self.input_data = data

    def get_output_data(self) -> Dict[str, Any]:
        """
        알고리즘 출력 데이터 반환

        Returns:
            알고리즘 출력 데이터
        """
        return self.output_data

    def get_history(self) -> List[Any]:
        """
        알고리즘 출력 데이터 반환

        Returns:
            알고리즘 출력 데이터
        """
        return self.execution_history

    @abstractmethod
    def initAlgorithm(self):
        pass

    def doProc(self):
        print('init Algorithm..',self.name)
        self.initAlgorithm()
        i = 0
        while True:
            if not self.databuf.empty():
                data = self.databuf.get()#print('run algorithm->',self.name,' : ',self.databuf.get())
                #print(data)
                res = self.execute(data)
                self.resBuf.put(res)
                #print('run algorithm->', self.name, ' : ', res)
            #print('run algorithm->',self.name)
            i += 1
            sleep(0.1)

    def doProcResimul(self):
        print('init Algorithm..',self.name)
        self.initAlgorithm()
        while True:
            if not self.databuf.empty():
                data = self.databuf.get()
                if data == "__DONE__":
                    break
                for sensor in data:
                    print(sensor.__dict__)
                res = self.execute(data)
                self.resBuf.put(res)

    def execute(self, input_data: Optional[SensorFrame] = None) -> Dict[str, Any]:
        if input_data is None:
            pass
        else:
            try:
                self.is_running = True

                start_time = time.time()

                # 입력 데이터가 제공되면 업데이트
                if input_data is not None:
                    self.set_input_data(input_data)

                # 알고리즘 처리
                results = self.runAlgo()

                # 출력 데이터 설정
                self.output_data['input'] = self.input_data
                self.output_data['output'] = results

                self.execution_time = time.time() - start_time

                # 실행 이력 업데이트
                # self.execution_history.append({
                #     'timestamp': time.time(),
                #     'input_keys': list(self.input_data.keys()),
                #     'output_keys': list(self.output_data.keys()),
                #     'execution_time': self.execution_time
                # })

                return self.output_data

            except Exception as e:
                raise {'error': f'알고리즘 실행 중 오류: {str(e)}'}
                #raise
            finally:
                self.is_running = False

    def preprocessing(self):
        self.refined_data = []

        for key, value in self.data.items():
            for val in self.input_data:
                self.refined_data.append(value[str(val)])

    def clear_data(self) -> None:
        """입력 및 출력 데이터 초기화"""
        self.input_data = {}
        self.output_data = {}