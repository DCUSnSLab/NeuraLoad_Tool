import os

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from procsManager import ProcsManager


class AlgorithmResimulation(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.serial_manager = serial_manager

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()

        self.loadAlgorithmFromFile()
        self.initUI()
        self.initTimer()

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

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        self.weight_layout = QVBoxLayout()
        #weight_layout1.addWidget(self.actual_weight_text)

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)
        #
        # weight_layout2 = QHBoxLayout()
        # weight_layout2.addWidget(self.actual_location_text)
        # weight_layout2.addWidget(self.actual_location_output)
        # weight_layout2.addStretch()
        # weight_layout2.setSpacing(10)
        #
        layout = QVBoxLayout()
        layout.addLayout(self.weight_layout)
        # layout.addLayout(weight_layout2)
        # layout.addWidget(self.weight_table)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        # btn_layout.addWidget(self.reset_btn)
        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addWidget(self.all_btn)
        layout1.addWidget(self.stop_btn)

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

    def finishAllAlgorithms(self):
        self.procmanager.terminate()