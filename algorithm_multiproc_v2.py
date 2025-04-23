import os
import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from datainfo import SCENARIO_TYPE_MAP
from procsManager import ProcsManager

class AlgorithmMultiProcV2(QWidget):
    def __init__(self, serial_manager, wt):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.serial_manager = serial_manager

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()

        self.weight_table = wt

        self.experiment_count = 0

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
        self.stop_btn.setEnabled(False)  # 알고리즘 프로세스가 시작해야 활성화됨

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        #weight Presentation layout
        self.weight_layout = QVBoxLayout()
        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)
        self.weightWidget = QWidget()
        self.weightWidget.setLayout(self.weight_layout)
        self.weightWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 실험 리스트뷰
        self.experimentList = QListWidget()
        self.experimentList.setFont(QFont("Arial", 12))
        self.experimentList.setFixedHeight(10 * 20)
        self.experimentList.setSelectionMode(QAbstractItemView.NoSelection)

        # 파일명 출력용 (ReadOnly)
        self.generatedFilenameLine = QLineEdit()
        self.generatedFilenameLine.setReadOnly(True)

        # 파일 라벨
        self.exFileLabel = QLineEdit('set File Label')
        fileLabelLayout = QHBoxLayout()
        fileLabelLayout.addWidget(QLabel("파일라벨 : "))
        fileLabelLayout.addWidget(self.exFileLabel)

        # 시나리오 콤보박스
        self.cbx_scenario = self.__getScenarioCBX()
        scenarioLayout = QHBoxLayout()
        scenarioLayout.addWidget(QLabel("시나리오 : "))
        scenarioLayout.addWidget(self.cbx_scenario)

        # 실험 횟수
        self.experimentCountLine = QLineEdit("0")
        self.experimentCountLine.setReadOnly(True)
        countLayout = QHBoxLayout()
        countLayout.addWidget(QLabel("실험횟수 : "))
        countLayout.addWidget(self.experimentCountLine)

        # 버튼
        self.startMeasureBtn = QPushButton('Start Measure', self)
        self.startMeasureBtn.clicked.connect(self.on_start_measure)

        self.finishMeasureBtn = QPushButton('Finish (Reset) Measure', self)
        self.finishMeasureBtn.clicked.connect(self.on_finish_measure)

        # weightControllerLayout 구성
        weightControllerLayout = QVBoxLayout()
        weightControllerLayout.addWidget(self.experimentList)
        weightControllerLayout.addLayout(self.weight_table)
        weightControllerLayout.addWidget(self.generatedFilenameLine)
        weightControllerLayout.addLayout(fileLabelLayout)
        weightControllerLayout.addLayout(scenarioLayout)
        weightControllerLayout.addLayout(countLayout)
        weightControllerLayout.addWidget(self.startMeasureBtn)
        weightControllerLayout.addWidget(self.finishMeasureBtn)

        # Button
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.all_btn)
        btn_layout.addWidget(self.stop_btn)

        leftMenu = QVBoxLayout()
        leftMenu.addWidget(groupbox)
        leftMenu.addLayout(btn_layout)
        leftMenuWidget = QWidget()
        leftMenuWidget.setLayout(leftMenu)
        leftMenuWidget.setFixedWidth(400)  # 원하는 너비로 설정

        layout2 = QHBoxLayout()
        layout2.addWidget(leftMenuWidget, alignment=Qt.AlignLeft)
        layout2.addLayout(weightControllerLayout)
        layout2.addWidget(self.weightWidget)

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
                label.setText(str(data['output']['weight']))

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

    def __getScenarioCBX(self) -> QComboBox:
        cbx_scenario = QComboBox()
        for key, value in SCENARIO_TYPE_MAP.items():
            text = f"{key}: {value['name']} ({value['description']})"
            cbx_scenario.addItem(text, userData=key)  # 표시될 텍스트, 실제 값은 key
        return cbx_scenario

    def on_start_measure(self):
        self.experiment_count += 1
        self.experimentCountLine.setText(str(self.experiment_count))

        label = self.exFileLabel.text().strip()
        scenario_name = self.cbx_scenario.currentText().split(":")[1].split("(")[0].strip()
        scenario_index = self.cbx_scenario.currentData()
        item_text = f"{label}_{self.cbx_scenario.currentText()}_{self.experiment_count}"
        self.experimentList.addItem(item_text)

        # 파일명 생성
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{label}_{scenario_name}_{now_str}.bin"
        self.generatedFilenameLine.setText(filename)

    def on_finish_measure(self):
        self.experiment_count = 0
        self.experimentCountLine.setText("0")
        self.cbx_scenario.setCurrentIndex(0)
        self.experimentList.clear()


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

        self.procmanager.startThread(callback=lambda: self.stop_btn.setEnabled(True))
        # self.stop_btn.setEnabled(True)

    def finishAllAlgorithms(self):
        self.procmanager.terminate()
        for weight in self.outputLabels:
                label = self.outputLabels[weight]
                label.setText('-')

        self.stop_btn.setEnabled(False)