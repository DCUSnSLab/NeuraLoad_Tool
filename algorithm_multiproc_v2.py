import os
import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

import experiment
from Algorithm.algorithmtype import ALGORITHM_TYPE
from GUIController import GUIController
from datainfo import SCENARIO_TYPE_MAP, SensorFrame, ExperimentData, AlgorithmData, AlgorithmFileHandler, SENSORLOCATION
from procsManager import ProcsManager
from weight_action import WeightTable, AlgorithmRunBox

import pyqtgraph as pg
import traceback
from collections import deque


class AlgorithmMultiProcV2(QWidget):
    def __init__(self, parent, serial_manager, wt):
        super().__init__()
        self.procmanager = ProcsManager(serial_manager)
        self.procmanager.on_ready(self.isAlgorithmReady)
        self.serial_manager = serial_manager

        self.ports = [sensor.port for sensor in self.serial_manager.sensors]
        self.port_colors = {
            'TopLeft': 'b',
            'BottomLeft': 'r',
            'TopRight': 'g',
            'BottomRight': 'orange',
            'IMU': 'yellow',
            'etc': 'purple',
            '' : 'gray'
        }
        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}
        self.initial_sensor_values = {}
        self.location = {}

        self.port_location = {
            'TopLeft': 0,
            'BottomLeft': 1,
            'TopRight': 2,
            'BottomRight': 3,
            'IMU': 4,
            'etc': 5,
        }

        self.init_plot = {}

        parent.on_AppExit(self.AppExithandle)

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()
        self.is_paused_global = True
        self.initial_active = False

        self.weight_table: WeightTable = wt

        self.isExperimentStarted = False
        self.experiment_count = 0
        self.measure_metaData: SensorFrame = None
        self.filehandler: dict = {}
        self.predictionBuffer = {}

        self.algoLayout = AlgorithmRunBox()
        self.initUI()
        self.initTimer()

    def initUI(self):
        self.algoLayout.loadAlgorithmFileList()
        self.algoLayout.start_btn.clicked.connect(self.run)
        self.algoLayout.all_btn.clicked.connect(self.run_all)
        self.algoLayout.stop_btn.clicked.connect(self.finishAllAlgorithms)
        self.files, self.algorithm_checkbox = self.algoLayout.getFileandCbx()

        #weight Presentation layout
        self.weight_layout = QVBoxLayout()
        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)
        self.weightWidget = QWidget()
        self.weightWidget.setLayout(self.weight_layout)
        self.weightWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 실험 리스트뷰
        self.experimentList = QListWidget()
        self.experimentList.setFont(QFont("Arial", 10))
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

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("Sensor Change")
        self.graph_change.setLabel("left", "Change")
        self.graph_change.setLabel("bottom", "Time")
        self.graph_change.addLegend(offset=(30, 30))
        self.graph_change.setMinimumWidth(500)

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Sensor Value")
        self.graph_value.setLabel("left", "Value")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.addLegend(offset=(30, 30))
        self.graph_value.setMinimumWidth(500)

        headers = [
            loc.name.title().replace('_', '')
            for loc in SENSORLOCATION
            if loc is not SENSORLOCATION.NONE
        ]

        self.sensor_table = QTableWidget(2, len(headers))
        self.sensor_table.setHorizontalHeaderLabels(headers)
        self.sensor_table.setVerticalHeaderLabels(['initial value', 'value'])
        self.sensor_table.setMaximumHeight(200)
        self.sensor_table.setMinimumHeight(150)
        self.sensor_table.setMaximumWidth(1000)
        self.sensor_table.setMinimumWidth(500)
        self.sensor_table.itemChanged.connect(self.table_item_changed)

        self.initial_sensor_btn = QPushButton('초기값', self)
        self.initial_sensor_btn.setCheckable(True)
        self.initial_sensor_btn.clicked.connect(self.inital_sensor_values_update)

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
        weightControllerLayout.addWidget(self.initial_sensor_btn)

        leftMenuWidget = QWidget()
        leftMenuWidget.setLayout(self.algoLayout)
        leftMenuWidget.setFixedWidth(400)  # 원하는 너비로 설정

        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graph_change)
        graph_layout.addWidget(self.graph_value)
        graph_layout.addWidget(self.sensor_table)

        layout2 = QHBoxLayout()
        layout2.addWidget(leftMenuWidget, alignment=Qt.AlignLeft)
        layout2.addLayout(weightControllerLayout)
        # self.weightWidget.setFixedWidth(800)
        layout2.addWidget(self.weightWidget)
        layout2.addLayout(graph_layout)

        self.setLayout(layout2)

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)

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
            output: AlgorithmData = data['output']
            frame.algorithms = output
            #print('file handler : ',self.filehandler, 'algoname : ',algo_name)
            fh:AlgorithmFileHandler = self.filehandler[algo_name]
            fh.add_frame(frame)

            if frame.measured:
                if algo_name not in self.predictionBuffer:
                    self.predictionBuffer[algo_name] = []
                self.predictionBuffer[algo_name].append(output)
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
        weights = self.weight_table.getWeights().copy()
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

            # 마지막 항목 수정
            last_idx = self.experimentList.count() - 1
            last_item = self.experimentList.item(last_idx)
            original_text = last_item.text()

            # 실측 무게
            measured_weight = sum(self.weight_table.getWeights())
            update_text = f"{original_text}\n--------------------------"
            update_text += f"\n실측무게 : {measured_weight:.2f}"

            # 알고리즘별 평균 결과 출력
            for algo_name, data_list in self.predictionBuffer.items():
                if not data_list:
                    continue
                avg_weight = sum(d.predicted_weight for d in data_list) / len(data_list)
                avg_position = sum(d.position for d in data_list) / len(data_list)
                avg_error = sum(d.error for d in data_list) / len(data_list)
                if measured_weight != 0:
                    error_rate = abs(avg_weight - measured_weight) / measured_weight * 100
                else:
                    error_rate = 0.0
                update_text += f"\n[{algo_name}] 평균예측무게: {avg_weight:.2f} (오차율: {error_rate:.2f}%), 위치: {avg_position:.2f}, 오차: {avg_error:.2f}"
            update_text += f"\n-----------------------------------------------------------------------------------------\n"

            last_item.setText(update_text)
            self.experimentList.scrollToBottom()
            self.predictionBuffer.clear()

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
        self.timer.start(1)  # 알고리즘 돌릴 때만 타이머가 작동하도록 설정
        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                print('run - ', cbx.text())
                if cbx.text() in self.files:
                    print('select algorithm file -> ',cbx.text(), self.files[cbx.text()])
                    self.procmanager.addProcess(self.files[cbx.text()])

        self.procmanager.startThread(callback=self.setBtnforRunAlgorithm)
        # self.stop_btn.setEnabled(True)

    def setBtnforRunAlgorithm(self):
        self.algoLayout.stop_btn.setEnabled(True)
        self.algoLayout.start_btn.setEnabled(False)
        self.algoLayout.all_btn.setEnabled(False)

    def finishAllAlgorithms(self):
        self.procmanager.terminateAll()
        for weight in self.outputLabels:
            label = self.outputLabels[weight]
            label.setText('-')

        self.timer.stop()

        self.algoLayout.stop_btn.setEnabled(False)
        self.algoLayout.start_btn.setEnabled(True)
        self.algoLayout.all_btn.setEnabled(True)
        self.on_finish_measure()
        self.toggleExperimentMenu(False)

    def AppExithandle(self):
        self.finishAllAlgorithms()

    def receive_sensor_data(self, send_data: list):
        try:
            self.save_graph_min = send_data[0]
            self.save_graph_max = send_data[1]
            port = send_data[2]
            location_name = send_data[3]
            y_value = float(send_data[4])

            if port not in self.location:
                self.location[port] = location_name

            self.graph_change.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)
            self.graph_value.getPlotItem().setYRange(min=0, max=800)

            if port not in self.plot_data:
                self.plot_data[port] = deque(maxlen=300)
                self.plot_change[port] = deque(maxlen=300)

            if port not in self.plot_curve:
                color = self.port_colors.get(location_name, 'gray')
                self.plot_curve[port] = self.graph_value.plot(
                    pen=pg.mkPen(color=color, width=2),
                    name=location_name
                )
                self.plot_curve_change[port] = self.graph_change.plot(
                    pen=pg.mkPen(color=color, width=2),
                    name=location_name
                )

            self.plot_data[port].append(y_value)

            if port in self.initial_sensor_values:
                changed = y_value - self.initial_sensor_values[port]
            else:
                changed = 0.0

            self.plot_change[port].append(changed)

            x = list(range(len(self.plot_data[port])))
            y = list(self.plot_data[port])
            y_change = list(self.plot_change[port])

            self.plot_curve[port].setData(x, y)
            # self.plot_curve_change[port].setData(x, y_change)

            col = self.port_location.get(location_name, 6)
            if port not in self.initial_sensor_values:
                self.initial_sensor_values[port] = y_value
                self.sensor_table.setItem(0, col, QTableWidgetItem(str(y_value)))
            self.sensor_table.setItem(1, col, QTableWidgetItem(str(y_value)))
            self.plot_curve_change[port].setData(x, y_change)

            if self.initial_active:
                self.sensor_table.setItem(0, col, QTableWidgetItem(str(y[-1])))

                if port not in self.init_plot:
                    self.init_plot[port] = deque(maxlen=300)

                self.init_plot[port].append(y_value)

        except Exception as e:
            print(f"receive_sensor_data 에러: {e}")

    def inital_sensor_values_update(self):
        if self.initial_sensor_btn.isChecked():
            self.initial_active = True
            self.is_paused_global = False
            self.countdown_value = 5

            self.initial_sensor_btn.setCheckable(False)
            self.initial_sensor_btn.setEnabled(False)

            def countdown():
                if self.countdown_value > 0:
                    self.initial_sensor_btn.setText(f"{self.countdown_value}초 남음")
                    self.countdown_value -= 1
                    QTimer.singleShot(1000, countdown)
                else:
                    # 5초 후: 실험 종료 상태로 변경
                    self.initial_sensor_btn.setChecked(False)  # 버튼 체크 해제
                    self.initial_active = False
                    self.is_paused_global = True
                    self.initial_sensor_btn.setText("초기값")
                    self.initial_sensor_btn.setCheckable(True)
                    self.initial_sensor_btn.setEnabled(True)
                    for port, value in list(self.init_plot.items()):
                        if len(value) > 0:
                            avg = sum(value) / len(value)

                            location_name = self.location[port]
                            col = self.port_location.get(location_name, 6)

                            self.sensor_table.setItem(0, col, QTableWidgetItem(str(avg)))
                            self.initial_sensor_values[port] = avg
                            self.inital_send_algorithm()

            self.init_plot.clear()
            countdown()  # 카운트다운 시작
            QCoreApplication.processEvents()
        else:
            self.initial_active = False
            self.is_paused_global = True
            self.initial_sensor_btn.setText("초기값")

    def inital_send_algorithm(self):
        return self.initial_sensor_values

    def table_item_changed(self, item: QTableWidgetItem):
        row = item.row()
        col = item.column()
        value = item.text()

        if row == 0:
            try:
                float_value = float(value)
                location_name = list(self.port_location.keys())[list(self.port_location.values()).index(col)]
                port = None
                for p, loc in self.location.items():
                    if loc == location_name:
                        port = p
                        break

                self.initial_sensor_values[port] = float_value
                self.inital_send_algorithm()
            except ValueError:
                QMessageBox.warning(self, "입력 오류", "숫자만 입력 가능합니다.")
                # 잘못된 입력일 경우 기존 값으로 복원
                location_name = list(self.port_location.keys())[list(self.port_location.values()).index(col)]
                for p, loc in self.location.items():
                    if loc == location_name:
                        port = p
                        break
                prev_value = self.initial_sensor_values.get(port, "")
                self.sensor_table.blockSignals(True)
                self.sensor_table.setItem(0, col, QTableWidgetItem(str(prev_value)))
                self.sensor_table.blockSignals(False)