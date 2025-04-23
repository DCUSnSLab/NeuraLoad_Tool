import os

from PyQt5.QtCore import QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from Algorithm.algorithmtype import ALGORITHM_TYPE
from file_manager import AlgorithmFileManager
from resimulation_manager import ResimulationManager


class AlgorithmResimulation(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.resimulManager = ResimulationManager(sm=serial_manager)
        self.serial_manager = serial_manager
        self.algoFile = AlgorithmFileManager()

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()
        self.filepath = None

        self.loadAlgorithmCbx()
        self.initUI()

    def initUI(self):
        self.algorithm_list = QWidget(self)

        self.toggleBtn = QPushButton("Step By Step OFF")
        self.toggleBtn.setCheckable(True)
        self.toggleBtn.setChecked(False)  # toggle 초기 상태
        self.toggleBtn.toggled.connect(self.changeToggle)
        self.toggleBtn.setMinimumSize(QSize(150, 50))
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.toggleBtn.setFont(font)
        self.fileBtn = QPushButton("Data File Load")
        self.fileBtn.clicked.connect(self.loadDataFile)
        self.fileBtn.setMinimumSize(QSize(120, 50))
        self.fileBtn.setFont(font)
        self.filenameLabel = QLabel("")
        self.filenameLabel.setMaximumHeight(50)

        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        for cbx in self.algorithm_checkbox:
            self.checkbox_layout.addWidget(cbx)

        self.start_btn = QPushButton('Run the selected algorithm', self)
        self.start_btn.clicked.connect(self.run)

        self.all_btn = QPushButton('Run all', self)
        self.all_btn.clicked.connect(self.run_all)

        self.stop_btn = QPushButton('Stop and Reset', self)
        self.stop_btn.clicked.connect(self.finishAllAlgorithms)
        self.stop_btn.setEnabled(False)  # 알고리즘 프로세스가 시작해야 활성화됨

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        self.weight_layout = QVBoxLayout()

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)

        layout = QVBoxLayout()
        layout.addLayout(self.weight_layout)

        top_layout = QHBoxLayout()  # 알고리즘, 버튼 박스와 분리를 위한 레이아웃
        top_layout.addWidget(self.toggleBtn)
        top_layout.addWidget(self.fileBtn)
        top_layout.addWidget(self.filenameLabel)
        top_layout.addStretch()  # 버튼 오른쪽 공간 채우기

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.all_btn)
        btn_layout.addWidget(self.stop_btn)

        layout1 = QVBoxLayout()
        layout1.addLayout(top_layout)
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

    def changeToggle(self, status):
        if status:
            self.toggleBtn.setText("Step By Step ON")
            self.all_btn.setEnabled(False)
        else:
            self.toggleBtn.setText("Step By Step OFF")
            self.all_btn.setEnabled(True)

    def loadDataFile(self):
        fname = QFileDialog.getOpenFileName(self)
        if not fname[0]:
            return
        self.filepath = fname[0]
        self.filenameLabel.setText(fname[0])

    def updateLabel(self):
        resbuf = self.procmanager.getResultBufs()
        for bname, val in resbuf.items():
            if not val.empty():
                data = val.get()
                print(bname, data)

    def loadAlgorithmCbx(self):
        for algo_name in ALGORITHM_TYPE.list_all():
            self.files[algo_name.name] = algo_name
            checkbox = QCheckBox(algo_name.name)
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
        self.resimulManager.getDataFile(self.filepath)
        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                print('run - ', cbx.text())
                if cbx.text() in self.files:
                    print('select algorithm file -> ',cbx.text(), self.files[cbx.text()])
                    self.resimulManager.addProcess(self.files[cbx.text()])

        self.resimulManager.startThread(callback=lambda: self.stop_btn.setEnabled(True))

    def finishAllAlgorithms(self):
        self.resimulManager.terminate()
        self.stop_btn.setEnabled(False)