import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from arduino_manager import SerialThread, get_arduino_ports
from experiment import Experiment
from multiprocessing import Process, Queue
import importlib.util
from AlgorithmInterface import AlgorithmBase


def run_algorithm_in_process(file_path, result_queue):
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, AlgorithmBase) and obj is not AlgorithmBase:
            instance = obj()
            while True:
                result = instance.execute()
                result_queue.put(str(result))

class Algorithm(QWidget):
    def __init__(self):
        super().__init__()
        self.threads = []
        self.ports = get_arduino_ports()
        self.select_file = []
        self.setupUI()
        self.setup()

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        self.load_files()

        self.start_btn = QPushButton('선택한 알고리즘 실행', self)
        self.start_btn.clicked.connect(self.start)

        self.reset_btn = QPushButton('리셋', self)
        self.reset_btn.clicked.connect(self.reset)

        self.file_name = QLabel()
        self.file_name.setText("실행 중: 없음")

        self.result_label = QLabel()
        self.result_label.setText(" - ")

        # self.stop_btn = QPushButton('정지(K)', self)
        # self.stop_btn.clicked.connect(self.stop)

        # self.restart_btn = QPushButton('재시작(L)', self)
        # self.restart_btn.clicked.connect(self.restart)

        # self.sensor_table = QTableWidget()
        # self.sensor_table.setColumnCount(len(self.ports))
        # self.sensor_table.setRowCount(1)
        # for i, port in enumerate(self.ports):
        #     self.sensor_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
        # self.sensor_table.setVerticalHeaderLabels(['value'])


    def load_files(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        self.files = []
        self.checkboxes = []

        for file_name in os.listdir(folder):
            full_path = os.path.join(folder, file_name)
            self.files.append((file_name, full_path))

            checkbox = QCheckBox(file_name)
            self.checkbox_layout.addWidget(checkbox)

            self.checkboxes.append(checkbox)

    def clear_checkboxes(self):
        while self.left_layout.count():
            child = self.left_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                self.select_file.clear()

    def start(self):
        self.select_file.clear()
        selected_names = []

        for checkbox, (file_name, full_path) in zip(self.checkboxes, self.files):
            if checkbox.isChecked():
                selected_names.append(file_name)

                # ✅ 큐 생성 및 저장
                self.result_queue = Queue()

                # ✅ 프로세스 실행 시 큐 전달
                p = Process(target=run_algorithm_in_process, args=(full_path, self.result_queue))
                p.start()
                self.threads.append(p)

                self.file_name.setText(", ".join(selected_names) + " 실행 결과:")

                # ✅ GUI에서 주기적으로 큐 확인
                self.timer = QTimer()
                self.timer.timeout.connect(self.update_result)
                self.timer.start(500)

    def reset(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

        for p in self.threads:
            if p.is_alive():
                p.terminate()
                p.join()
        self.threads.clear()
        if hasattr(self, 'timer'):
            self.timer.stop()

        self.file_name.setText("실행 중: 없음")
        self.result_label.setText(" - ")

    def update_result(self):
        if self.result_queue and not self.result_queue.empty():
            result = self.result_queue.get()
            self.result_label.setText(result)

    def closeEvent(self, event):
        # 창 닫힐 때 백그라운드 프로세스 모두 정리
        for p in self.threads:
            if p.is_alive():
                p.terminate()
                p.join()
        self.threads.clear()

        if hasattr(self, 'timer'):
            self.timer.stop()

        event.accept()  # 창 닫기 허용

    # def stop(self):
    #     for thread in self.threads:
    #         thread.pause()
    #     QCoreApplication.processEvents()

    # def restart(self):
    #     for thread in self.threads:
    #         thread.resume()

    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('현재 사용 가능한 알고리즘')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        # btn_layout1 = QHBoxLayout()
        # btn_layout1.addWidget(self.stop_btn)
        # btn_layout1.addWidget(self.restart_btn)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        # layout1.addLayout(btn_layout1)

        layout3 = QHBoxLayout()
        layout3.addWidget(self.file_name)
        layout3.addWidget(self.result_label)

        layout4 = QHBoxLayout()
        layout4.addLayout(layout1)
        # layout4.addWidget(self.sensor_table)
        layout4.addLayout(layout3)

        self.setLayout(layout4)

if __name__ == '__main__':
   Process.freeze_support()
   app = QApplication(sys.argv)
   ex = Algorithm()
   sys.exit(app.exec_())