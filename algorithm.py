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
        self.experiment.subscribers.append(self)
        self.weight_total = [0] * 9
        self.weight_location = [0] * 9
        self.selected_names = []
        self.setupUI()
        self.setup()

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        self.load_files()

        self.start_btn = QPushButton('Run the selected algorithm', self)
        self.start_btn.clicked.connect(self.start)

        self.reset_btn = QPushButton('Reset', self)
        self.reset_btn.clicked.connect(self.reset)

        self.all_btn = QPushButton('Run all', self)
        self.all_btn.clicked.connect(self.run)

        self.actual_weight_text = QLabel('Actual Weight:')
        self.actual_weight_output = QLabel("-")
        self.actual_weight_kg = QLabel("kg")

        self.actual_location_text = QLabel('Actual Location:')
        self.actual_location_output = QLabel("-")
        self.weight_update()

        self.weight_table = QTableWidget()

    def load_files(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]
        self.files = []
        self.checkboxes = []

        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files.append((file_name, full_path))

            checkbox = QCheckBox(file_name)
            self.checkbox_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

    def start(self):
        for checkbox, (file_name, full_path) in zip(self.checkboxes, self.files):
            if checkbox.isChecked():
                self.selected_names.append(file_name)

        self.weight_table.setColumnCount(len(self.selected_names))
        self.weight_table.setRowCount(3)
        self.weight_table.setVerticalHeaderItem(0, QTableWidgetItem('추정 무게'))
        self.weight_table.setVerticalHeaderItem(1, QTableWidgetItem('추정 위치'))
        self.weight_table.setVerticalHeaderItem(2, QTableWidgetItem('오차율'))

        for i in range(len(self.selected_names)):
            self.weight_table.setHorizontalHeaderItem(i, QTableWidgetItem(self.selected_names[i]))

        self.weight_table.resizeColumnsToContents()

    def reset(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

        if self.selected_names:
            self.selected_names.clear()

        self.weight_table.setColumnCount(len(self.selected_names))
        self.weight_table.setRowCount(0)

        for i in range(len(self.selected_names)):
            self.weight_table.setHorizontalHeaderItem(i, QTableWidgetItem(self.selected_names[i]))

    def run(self):
        for checkbox, (file_name, full_path) in zip(self.checkboxes, self.files):
            self.selected_names.append(file_name)
            checkbox.setChecked(True)

        self.weight_table.setColumnCount(len(self.selected_names))
        self.weight_table.setRowCount(3)
        self.weight_table.setVerticalHeaderItem(0, QTableWidgetItem('추정 무게'))
        self.weight_table.setVerticalHeaderItem(1, QTableWidgetItem('추정 위치'))
        self.weight_table.setVerticalHeaderItem(2, QTableWidgetItem('오차율'))

        for i in range(len(self.selected_names)):
            self.weight_table.setHorizontalHeaderItem(i, QTableWidgetItem(self.selected_names[i]))

        self.weight_table.resizeColumnsToContents()

    def weight_update(self):
        self.weight_total = sum(self.weight_total)
        all_weight_location = list(filter(lambda x: self.weight_location[x] == 1, range(len(self.weight_location))))
        all_weight_location = [i+1 for i in all_weight_location]

        if sum(all_weight_location) == 0:
            self.actual_location_output.setText("0")
        else:
            self.actual_location_output.setText(str(all_weight_location))

        self.actual_weight_output.setText(str(self.weight_total))

    def set_weight(self, weight_a):
        self.weight_total = weight_a
        self.weight_location = [0] * len(weight_a)
        for i in range (len(self.weight_total)):
            if self.weight_total[i] > 0:
                self.weight_location[i] = 1
        self.weight_update()


    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        weight_layout1 = QHBoxLayout()
        weight_layout1.addWidget(self.actual_weight_text)
        weight_layout1.addWidget(self.actual_weight_output)
        weight_layout1.addWidget(self.actual_weight_kg)
        weight_layout1.addStretch()
        weight_layout1.setSpacing(10)

        weight_layout2 = QHBoxLayout()
        weight_layout2.addWidget(self.actual_location_text)
        weight_layout2.addWidget(self.actual_location_output)
        weight_layout2.addStretch()
        weight_layout2.setSpacing(10)

        layout = QVBoxLayout()
        layout.addLayout(weight_layout1)
        layout.addLayout(weight_layout2)
        layout.addWidget(self.weight_table)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addWidget(self.all_btn)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Algorithm()
   sys.exit(app.exec_())