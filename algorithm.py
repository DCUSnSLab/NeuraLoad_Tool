import copy
import os
import sys
import importlib.util
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from arduino_manager import SerialThread, get_arduino_ports
from experiment import Experiment
from AlgorithmInterface import AlgorithmBase

class Algorithm(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.experiment = Experiment(serial_manager)
        self.setupUI()
        self.setup()

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        # self.load_files()

        self.start_btn = QPushButton('선택한 알고리즘 실행', self)
        # self.start_btn.clicked.connect(self.start)
        print('무게', self.experiment.weight_a)

        self.reset_btn = QPushButton('리셋', self)
        # self.reset_btn.clicked.connect(self.reset)

        # self.actual_weight_text = QLabel('Actual Weight:')
        # self.actual_weight_output = QLabel()
        #
        # self.actual_location_text = QLabel('Actual Location:')
        # self.actual_location_output = QLabel()
        #
        # self.weight_table = QTableWidget()
        # self.weight_table.setCurrentCell()
        # self.weight_table.setRowCount(3)
        # for i in range()

    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)

        self.setLayout(layout1)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Algorithm()
   sys.exit(app.exec_())