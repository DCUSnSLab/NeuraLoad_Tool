import os
import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from procsManager import ProcsManager

class AlgorithmMultiProc(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.serial_manager = serial_manager

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()

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

        self.weight_table = QTableWidget(3, 3)
        self.weight_table.installEventFilter(self)
        self.weight_table.cellChanged.connect(self.onCellChanged)
        self.weight_table.setMinimumHeight(200)

        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(self.weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(lambda: self.weight_update(True))

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(lambda: self.weight_update(False))

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        self.weight_layout = QVBoxLayout()
        #weight_layout1.addWidget(self.actual_weight_text)

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)

        layout_btn = QHBoxLayout()
        layout_btn.addWidget(self.weight_btn_p)
        layout_btn.addWidget(self.weight_btn_m)

        layout_w = QVBoxLayout()
        layout_w.addWidget(self.weight_table)
        layout_w.addLayout(layout_btn)

        #
        # weight_layout2 = QHBoxLayout()
        # weight_layout2.addWidget(self.actual_location_text)
        # weight_layout2.addWidget(self.actual_location_output)
        # weight_layout2.addStretch()
        # weight_layout2.setSpacing(10)
        #
        layout = QVBoxLayout()
        layout.addLayout(layout_w)
        layout.addLayout(self.weight_layout)
        # layout.addLayout(weight_layout2)
        # layout.addWidget(self.weight_table)

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

    def loadAlgorithmFromFile(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]

        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files[file_name] = full_path
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

        self.procmanager.start()
        self.stop_btn.setEnabled(True)

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

    def onCellChanged(self, row, col):
        try:
            item = self.weight_table.item(row, col)
            if item is None:
                return

            new_value = item.text().strip()
            index = row * 3 + col

            if 0 <= index < len(self.weight_a):
                try:
                    self.weight_a[index] = int(new_value)
                    self.broadcast_weight()
                except ValueError:
                    prev_value = self.weight_a[index]
                    item.setText(str(prev_value))
            else:
                prev_value = -1
                item.setText(str(prev_value))
            self.data_update()

        except Exception as e:
            print(f"onCellChanged 오류: {e}")
            # 로그 출력 객체가 있는지 확인
            if hasattr(self, 'log_output'):
                self.log_output.append(f"onCellChanged 오류: {e}")


    # +, - 버튼
    def weight_update(self, TF):
        selected_items = self.weight_table.selectedItems()
        if selected_items:
            for val in selected_items:
                text = val.text().strip()
                current_value = int(text)

                row = val.row()
                col = val.column()

                index = row * 3 + col

                if TF:
                    if self.weight_a[index] == -1:
                        self.weight_a[index] = (current_value + 21)
                    else:
                        self.weight_a[index] = (current_value + 20)
                else:
                    if 0 <= index < len(self.weight_a):
                        if current_value < 20:
                            self.weight_a[index] = 0
                        else:
                            self.weight_a[index] = current_value - 20
                val.setText(str(self.weight_a[index]))
                self.data_update()

    def table_update(self, weight_a):
        self.weight_table.clear()
        self.count = 0
        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1