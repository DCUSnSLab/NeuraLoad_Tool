import os
import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from Algorithm.algorithmtype import ALGORITHM_TYPE
from datainfo import SCENARIO_TYPE_MAP, SensorFrame, ExperimentData, AlgorithmData, AlgorithmFileHandler
from procsManager import ProcsManager
from weight_action import WeightTable


class AlgorithmMultiProcV2(QWidget):
    def __init__(self, serial_manager, wt):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.procmanager.on_ready(self.isAlgorithmReady)
        self.serial_manager = serial_manager

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()

        self.weight_table: WeightTable = wt

        self.isExperimentStarted = False
        self.experiment_count = 0
        self.measure_metaData: SensorFrame = None
        self.filehandler: dict = {}

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
        self.experimentList.setFixedHeight(10 * 50)
        self.experimentList.setSelectionMode(QAbstractItemView.NoSelection)

        # 파일명 출력용 (ReadOnly)
        self.generatedFilenameLine = QLineEdit()
        self.generatedFilenameLine.setReadOnly(True)

        # 파일 라벨
        self.exFileLabel = QLineEdit('')
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

        self.toggleExperimentMenu(False)

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
        self.timer.timeout.connect(self.updateData)
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

    def toggleExperimentMenu(self, Enabled:bool=True):
        self.exFileLabel.setEnabled(Enabled)
        self.cbx_scenario.setEnabled(Enabled)
        self.experimentCountLine.setEnabled(Enabled)
        self.startMeasureBtn.setEnabled(Enabled)
        self.finishMeasureBtn.setEnabled(Enabled)

    def isAlgorithmReady(self):
        self.toggleExperimentMenu(True)

    def updateData(self):
        resbuf = self.procmanager.getResultBufs()
        for algo_name, val in resbuf.items():
            if not val.empty():
                data = val.get()
                #print(algo_name, data)
                self.updateAlgorithmFile(algo_name, data)

                self.updateLabel(algo_name, data['output'])

    def updateLabel(self, algo_name, data: AlgorithmData):
        label = self.outputLabels[algo_name]
        label.setText(str(data.predicted_weight))

    def updateAlgorithmFile(self, algo_name, data):
        if self.isExperimentStarted and len(self.filehandler) > 0:
            algotype = ALGORITHM_TYPE.from_name(algo_name)
            frame: SensorFrame = data['input']
            output = data['output']
            frame.algorithms = output
            #print('file handler : ',self.filehandler, 'algoname : ',algo_name)
            fh:AlgorithmFileHandler = self.filehandler[algo_name]
            fh.add_frame(frame)
            # print('output -> ',output)
            # print('input -> ',frame)

            # if fh is not None and fh.isRunning():
            #     self.filehandler


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
        weights = self.weight_table.getWeights()
        item_text = f"실험 {self.experiment_count} 회차 : {label}_{self.cbx_scenario.currentText()}_{weights}"
        self.experimentList.addItem(item_text)

        # 파일명 생성
        now_str = datetime.datetime.now().strftime("%Y%m%d")
        filename = f"_{label}_{scenario_name}_{now_str}.bin"
        filename = self.filenameGenerator(label, scenario_name, now_str)
        self.generatedFilenameLine.setText(filename)

        dataGroup = {'label': label, 'scenario': scenario_index, 'numofex': self.experiment_count, 'weights': weights,
                     'filename': filename}
        self.setFileHandle(True, dataGroup)
        self.startExperiment(dataGroup)
        print('before message box')
        # 경고 메시지 박스 표시
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("주의")
        msg.setText("차량에 화물을 올리십시오")
        msg.setStandardButtons(QMessageBox.Ok)
        result = msg.exec_()

        if result == QMessageBox.Ok:
            for fh in self.filehandler.values():
                fh.setExperimentInfo(isMeasureStarted=True)

        print('after message box')

        # 버튼 비활성화 및 출력
        self.startMeasureBtn.setEnabled(False)
        print("버튼창 비활성화")

        # 버튼 비활성화 및 메시지 출력
        self.startMeasureBtn.setEnabled(False)
        print("버튼창 비활성화")

        # 5초 카운트다운 시작
        self.countdown = 5
        self.startMeasureBtn.setText(f"Start Measure ({self.countdown})")

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # 1초마다 호출

    def filenameGenerator(self, label: str, scenario: str, now_str: str) -> str:
        if label == '':
            return f"_{scenario}_{now_str}.bin"
        else:
            return f"_{label}_{scenario}_{now_str}.bin"

    def update_countdown(self):
        self.countdown -= 1
        if self.countdown > 0:
            self.startMeasureBtn.setText(f"Start Measure ({self.countdown})")
        else:
            self.countdown_timer.stop()
            self.startMeasureBtn.setEnabled(True)
            self.startMeasureBtn.setText("Start Measure")
            self.stopExperiment()

    #실험을 완전 종료하고 새로운 실험을 시작(파일을 새로 만들고 싶을 때) 실행
    def on_finish_measure(self):
        self.experiment_count = 0
        self.experimentCountLine.setText("0")
        self.cbx_scenario.setCurrentIndex(0)
        self.experimentList.clear()
        self.setFileHandle(False)
        self.measure_metaData = None
        self.isExperimentStarted = False

    #파일 핸들러 등록
    def setFileHandle(self, isStartButton: bool, meta: {} = None):
        print('before = ',self.filehandler)
        if isStartButton:
            for sel_algo in self.algorithm_checkbox:
                if sel_algo.isChecked():
                    fh = AlgorithmFileHandler(sel_algo.text()+meta['filename'])
                    self.filehandler[sel_algo.text()] = fh
        else: #is Finished
            for fh in self.filehandler.values():
                fh.stop_auto_save()
            self.filehandler.clear()


        print('after = ',self.filehandler)

    #측정 시작시 실험 데이터 초기화 및 파일핸들러 시작(이미 시작되어 있으면 패스)
    def startExperiment(self, meta):
        #set Meta
        self.isExperimentStarted = True
        self.measure_metaData = SensorFrame(timestamp=None,
                                            sensors=None,
                                            scenario=meta['scenario'],
                                            started=self.isExperimentStarted,
                                            measured=False,
                                            NofExperiments=meta['numofex'],
                                            experiment=ExperimentData(meta['weights']),
                                            algorithms=None)

        for fh in self.filehandler.values():
            if fh is not None and fh.isRunning() is False:
                fh.start_auto_save(meta=self.measure_metaData)
        print('start Experiment!!!')

    #실험을 시작한 후 다음 실험을 위해 대기
    def stopExperiment(self):
        for fh in self.filehandler.values():
            fh.setExperimentInfo(isExperimentStarted=False, isMeasureStarted=False)
        self.isExperimentStarted = False

    def loadAlgorithmFromFile(self):
        for algo_name in ALGORITHM_TYPE.list_all():
            self.files[algo_name.name] = algo_name
            checkbox = QCheckBox(algo_name.name)
            self.algorithm_checkbox.append(checkbox)

    def loadAlgorithmFromFile_legacy(self):
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
                    self.procmanager.addProcess(self.files[cbx.text()])

        self.procmanager.startThread(callback=lambda: self.stop_btn.setEnabled(True))
        # self.stop_btn.setEnabled(True)

    def finishAllAlgorithms(self):
        self.procmanager.terminate()
        for weight in self.outputLabels:
                label = self.outputLabels[weight]
                label.setText('-')

        self.stop_btn.setEnabled(False)
        self.on_finish_measure()
        self.toggleExperimentMenu(False)