import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from arduino_manager import SerialThread, get_arduino_ports
from experiment import Experiment

class Algorithm(QWidget):
    def __init__(self):
        super().__init__()
        self.threads = []
        self.ports = get_arduino_ports()
        self.port_location = {}
        self.port_colors = {}
        self.port_index = {}
        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}

        self.weight_a = [0] * 9

        self.setting()
        self.setupUI()
        self.setup()

    def set_weight(self, weight):
        self.weight_a = weight.copy()

    def setting(self):
        for i, port in enumerate(self.ports):
            if i == 0:
                name = 'TopLeft'
                color = 'r'
            elif i == 1:
                name = 'BottomLeft'
                color = 'g'
            elif i == 2:
                name = 'LeftRight'
                color = 'b'
            elif i == 3:
                name = 'RightLeft'
                color = 'orange'
            elif i == 4:
                name = 'IMU'
                color = 'yellow'
            else:
                name = ''
                color = 'purple'

            self.port_location[port] = name
            self.port_colors[name] = color
            self.port_index[port] = i

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        self.load_files()

        self.start_btn = QPushButton('선택한 알고리즘 실행', self)
        self.start_btn.clicked.connect(self.start)

        self.reset_btn = QPushButton('리셋', self)
        self.reset_btn.clicked.connect(self.reset)

        self.sensor_table = QTableWidget()
        self.sensor_table.setColumnCount(len(self.ports))
        self.sensor_table.setRowCount(1)
        for i, port in enumerate(self.ports):
            name = self.port_location.get(port, "")
            self.sensor_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
        self.sensor_table.setVerticalHeaderLabels(['value'])

        self.logging = QTableWidget()
        self.logging.setColumnCount(3)
        self.logging.setHorizontalHeaderLabels(['무게', '위치', '로그'])
        self.logging.setMinimumHeight(150)
        self.logging.setMinimumWidth(150)
        self.logging.horizontalHeader().setStretchLastSection(True)

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("Sensor Change")
        self.graph_change.setLabel("left", "Change")
        self.graph_change.setLabel("bottom", "Time")
        self.graph_change.addLegend(offset=(30, 30))
        self.graph_change.setMinimumWidth(500)

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Sensor")
        self.graph_value.setLabel("left", "Value")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.setMinimumWidth(500)

        for port in self.ports:
            self.plot_data[port] = deque(maxlen=300)
            self.plot_change[port] = deque(maxlen=300)
            color = self.port_colors.get(self.port_location[port])

            self.plot_curve[port] = self.graph_value.plot(
                pen=pg.mkPen(color=color, width=1),
                name=self.port_location.get(port, port)
            )

            self.plot_curve_change[port] = self.graph_change.plot(
                pen=pg.mkPen(color=color, width=1),
                name=self.port_location.get(port, port)
            )

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #F2F2F2;")

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

    def update_data(self, port, data):
        if port in self.port_index:
            try:
                value = int(data.strip())
            except ValueError:
                return

            self.plot_data[port].append(value)
            self.plot_change[port].append(value)

            x = list(range(len(self.plot_data[port])))
            y = list(self.plot_data[port])

            base_val = self.plot_change[port][0] if len(self.plot_change[port]) > 0 else 0
            change = [v - base_val for v in self.plot_change[port]]

            self.plot_curve[port].setData(x, y)
            self.plot_curve_change[port].setData(x, change)

            location = self.port_index[port]
            self.sensor_table.setItem(0, location, QTableWidgetItem(data))

            current_row = self.logging.rowCount()
            self.logging.insertRow(current_row)
            self.logging.setItem(current_row, 0, QTableWidgetItem(str(self.weight_a)))

            name = self.port_location.get(port, "")
            self.logging.setItem(current_row, 1, QTableWidgetItem(name))

            self.logging.setItem(current_row, 2, QTableWidgetItem(data))
            self.logging.scrollToBottom()

    def start(self):
        pass

    def reset(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('현재 사용 가능한 알고리즘')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addWidget(self.logging)

        layout2 = QVBoxLayout()
        layout2.addWidget(self.sensor_table)
        layout2.addWidget(self.graph_change)
        layout2.addWidget(self.graph_value)

        layout3 = QVBoxLayout()
        layout3.addWidget(self.log_output)

        layout4 = QHBoxLayout()
        layout4.addLayout(layout1)
        layout4.addLayout(layout2)
        layout4.addLayout(layout3)

        self.setLayout(layout4)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Algorithm()
   sys.exit(app.exec_())
