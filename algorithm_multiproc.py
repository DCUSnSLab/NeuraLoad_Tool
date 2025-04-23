import os
import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from file_manager import AlgorithmFileManager
from procsManager import ProcsManager

class AlgorithmMultiProc(QWidget):
    def __init__(self, serial_manager, wt):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.serial_manager = serial_manager
        self.algofile = AlgorithmFileManager()

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()

        self.weight_table = wt

        self.real_weight = None
        self.real_position = None
        self.rate = 0

        self.weight_a = [-1] * 9
        self.count = 0
        self.is_syncing = False

        self.subscribers = []

        self.loadAlgorithmFromFile()
        self.initUI()
        self.initTimer()

    def add_subscriber(self, subscriber):
        self.subscribers.append(subscriber)

    def broadcast_weight(self):
        for sub in self.subscribers:
            # 각 subscriber가 set_weight 메소드를 가지고 있는지 확인
            if hasattr(sub, 'set_weight'):
                sub.set_weight(self.weight_a)

    def initUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        for cbx in self.algorithm_checkbox:
            self.checkbox_layout.addWidget(cbx)

        self.start_btn = QPushButton('Run the selected algorithm', self)
        self.start_btn.clicked.connect(self.run)

        # self.reset_btn = QPushButton('Reset', self)
        # self.reset_btn.clicked.connect(self.reset)

        self.all_btn = QPushButton('Run all', self)
        self.all_btn.clicked.connect(self.run_all)

        self.stop_btn = QPushButton('Stop and Reset', self)
        self.stop_btn.clicked.connect(self.finishAllAlgorithms)
        self.stop_btn.setEnabled(False)  # 알고리즘 프로세스가 시작해야 활성화됨

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(lambda: self.weight_update(True))

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(lambda: self.weight_update(False))

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        self.weight_layout = QVBoxLayout()

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)

        layout_btn = QHBoxLayout()
        layout_btn.addWidget(self.weight_btn_p)
        layout_btn.addWidget(self.weight_btn_m)

        layout_w = QVBoxLayout()
        layout_w.addWidget(self.weight_table)
        layout_w.addLayout(layout_btn)

        layout = QVBoxLayout()
        layout.addLayout(layout_w)
        layout.addLayout(self.weight_layout)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.all_btn)
        btn_layout.addWidget(self.stop_btn)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateLabel)
        self.timer.start(50)

    def setOutputLabels(self):
        self.clear_layout(self.weight_layout)

        font = QFont()
        font.setPointSize(30)
        font.setBold(True)

        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                layout = QHBoxLayout()
                label1 = QLabel(cbx.text())
                label1.setFont(font)
                layout.addWidget(label1)
                dataLabel = QLabel('-')
                dataLabel.setFont(font)
                layout.addWidget(dataLabel)
                self.weight_layout.addLayout(layout)
                self.outputLabels[cbx.text()] = dataLabel

    def updateLabel(self):
        resbuf = self.procmanager.getResultBufs()
        for bname, val in resbuf.items():
            if not val.empty():
                data = val.get()
                print(bname, data)
                label = self.outputLabels[bname]
                label.setText(str(data['weight']))
                self.data_save(bname, data)

    def clear_layout(self, layout):
        self.outputLabels.clear()
        while layout.count():
            print('delete layout - ',layout)
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            # layout 안에 또 다른 layout이 있을 수 있으므로 재귀적으로 처리
            elif item.layout() is not None:
                self.clear_layout(item.layout())
    def loadAlgorithmCbx(self):
        self.files = self.algofile.loadAlgorithmFromFile()
        for file_name in self.files:
            checkbox = QCheckBox(file_name)
            self.algorithm_checkbox.append(checkbox)

    def run(self):
        if not any(cbx.isChecked() for cbx in self.algorithm_checkbox):
            print('No checkbox selected')
            return
        self.runAlgorithm()

    def run_all(self):
        for cbx in self.algorithm_checkbox:
            cbx.setChecked(True)
        self.runAlgorithm()

    def runAlgorithm(self):
        self.setOutputLabels()
        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                print('run - ', cbx.text())
                if cbx.text() in self.files:
                    print('select algorithm file -> ',cbx.text(), self.files[cbx.text()])
                    self.procmanager.addProcess(cbx.text())

        self.procmanager.startThread(callback=lambda: self.stop_btn.setEnabled(True))
        # self.stop_btn.setEnabled(True)

    def finishAllAlgorithms(self):
        self.procmanager.terminate()
        for weight in self.outputLabels:
                label = self.outputLabels[weight]
                label.setText('-')

        self.stop_btn.setEnabled(False)

    def data_update(self):
        self.real_weight = sum(w if w != -1 else 0 for w in self.weight_a)
        self.real_position = [i + 1 for i, val in enumerate(self.weight_a) if val != -1]

    # 실제 무게 및 적재 위치 저장
    def set_weight(self, weight_a):
        self.data_update()
        if self.is_syncing:
            return

        self.is_syncing = True

        self.weight_a = weight_a.copy()
        self.weight_table.blockSignals(True)

        self.table_update(self.weight_a)

        self.weight_table.blockSignals(False)

        self.is_syncing = False

    # 오차율 계산
    def error_rate_cal(self, algo_weight):
        if  self.real_weight and algo_weight is not None:
            self.rate = ((abs(self.real_weight) - abs(algo_weight)) / self.real_weight) * 100

    #알고리즘 데이터 저장
    def data_save(self, bname, data):
        os.makedirs('algorithms_result', exist_ok=True)
        filename = datetime.datetime.now().strftime(bname+'_%y%m%d.txt')
        data_file = open(os.path.join('algorithms_result', filename), 'a', encoding='utf-8')

        timestamp = datetime.datetime.now().strftime('%H%M%S')

        last_data = data
        algo_position = int(last_data['position'])
        algo_weight = float(last_data['weight'])

        self.error_rate_cal(algo_weight)

        log_line = f'{timestamp}\t{self.real_weight}\t{self.real_position}\t{algo_weight}\t{algo_position}\t{self.rate}\n'

        if self.real_weight and algo_weight is not None:
            data_file.write(log_line)
            data_file.flush()
