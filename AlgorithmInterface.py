from abc import *
from PyQt5.QtWidgets import QApplication
from arduino_manager import store_algorithm
import sys

class AlgorithmInterface():
    def __init__(self):
        '''
        self.name: 알고리즘 파일 이름
        self.input: 들어오는 센서값
        self.model: 알고리즘 모델 경로
        self.weights: 현재 무게
        self.position: 현재 무게의 위치
        '''

        self.name = None
        self.input = None
        self.model = None
        self.weights = None
        self.position = None

        print(store_algorithm.get_value())

    def run(self):
        ...
        while self.is_running:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    self.data_store2.update(data)
                    print(f"[쓰레드] 수신: {data}")
                    print(f"[쓰레드] 현재 저장소: {list(self.data_store2.get_value())}")

    @abstractmethod
    def getdata(self):
        '''
        추정 무게 값 리턴(float)
        추정 무게 위치 값 리턴(int)
        '''
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    algo = AlgorithmInterface()  # ← ✅ 이 줄이 없으면 아무것도 실행되지 않음
    sys.exit(app.exec_())