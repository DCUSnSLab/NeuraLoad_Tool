from collections import deque
from typing import List

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *

from GUI_MAEGraph import BarGraphWidget
from GUI_graph_NR import GraphWidget
from GUI_progressbar import ProgressWidget
from datainfo import SensorFrame, AlgorithmData, SensorBinaryFileHandler
from resimulation_manager import ResimulationManager
from weight_action import AlgorithmRunBox


class AlgorithmResimulation(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.resimulManager = ResimulationManager(sm=serial_manager)
        self.serial_manager = serial_manager

        self.files = dict()  # Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = dict()
        self.filepath = None

        self.loadedData = None
        self.ResimData = None
        self.makedData = dict()

        self.algoLayout = AlgorithmRunBox()
        self.initUI()

    def initUI(self):
        # 상단 토글 버튼 (Step by Step)
        self.toggleBtn = QPushButton("Step by Step OFF")
        self.toggleBtn.setCheckable(True)
        self.toggleBtn.setChecked(False)  # toggle 초기 상태
        self.toggleBtn.toggled.connect(self.changeToggle)
        self.toggleBtn.setMinimumSize(QSize(150, 50))
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.toggleBtn.setFont(font)

        # 리시뮬레이션을 위한 파일 로드 버튼
        self.fileBtn = QPushButton("Data File Load")
        self.fileBtn.clicked.connect(self.On_loadDataFile)
        self.fileBtn.setMinimumSize(QSize(120, 50))
        self.fileBtn.setFont(font)
        self.filenameLabel = QLabel("")
        self.filenameLabel.setMaximumHeight(50)

        # 알고리즘 목록과 관련 버튼
        self.algoLayout.loadAlgorithmFileList()
        self.algoLayout.start_btn.clicked.connect(self.run)
        self.algoLayout.all_btn.clicked.connect(self.run_all)
        self.algoLayout.stop_btn.clicked.connect(self.finishAllAlgorithms)
        self.files, self.algorithm_checkbox = self.algoLayout.getFileandCbx()

        self.weight_layout = QVBoxLayout()

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)

        layout = QVBoxLayout()
        layout.addLayout(self.weight_layout)

        # 프로그래스바
        self.progress_widget = ProgressWidget(title="Algorithm Progress")
        self.progress_widget.set_total(100)

        # 체크박스
        self.view_only_measured_checkbox = QCheckBox("View Only Measured Data")
        self.view_only_measured_checkbox.setChecked(True)
        self.view_only_measured_checkbox.stateChanged.connect(self.onCheckboxToggled)

        # 센서 데이터 타입 선택 콤보박스 추가
        self.sensor_data_type_combo = QComboBox()
        self.sensor_data_type_combo.addItem("Sensor Distance")
        self.sensor_data_type_combo.addItem("Sensor diff (from reference Value)")
        self.sensor_data_type_combo.addItem("Filtered Sensor diff (from Low-Pass Filter)")
        self.sensor_data_type_combo.addItem("Filtered Sensor diff (from Moving Average Filter)")
        self.sensor_data_type_combo.currentIndexChanged.connect(self.onSensorDataTypeChanged)

        # Graph Widget
        self.graph_widget = GraphWidget(title="Algorithm Output Graph")
        self.sensor_graph_widget = GraphWidget(title="Sensor Distance Graph")  # 새로 추가한 센서 그래프 위젯
        self.mae_graph_widget = BarGraphWidget(title="MAE Comparison")
        # self.mse_graph_widget = BarGraphWidget(title="MSE Comparison")
        self.rmse_graph_widget = BarGraphWidget(title="RMSE Comparison")
        self.error_graph_widget = BarGraphWidget(title="Error Rate Comparison")

        main_graph_layout = QVBoxLayout()
        main_graph_layout.addWidget(self.sensor_graph_widget)
        main_graph_layout.addWidget(self.graph_widget)

        graph_layout = QHBoxLayout()
        graph_layout.addLayout(main_graph_layout, stretch=7)
        graph_layout.addWidget(self.mae_graph_widget, stretch=1)  # MAE 그래프 영역 3
        graph_layout.addWidget(self.rmse_graph_widget, stretch=1)  # RMSE 그래프 영역 3
        graph_layout.addWidget(self.error_graph_widget, stretch=1)

        top_layout = QHBoxLayout()  # 알고리즘, 버튼 박스와 분리를 위한 레이아웃
        top_layout.addWidget(self.toggleBtn)
        top_layout.addWidget(self.fileBtn)
        top_layout.addWidget(self.filenameLabel)
        top_layout.addStretch()  # 버튼 오른쪽 공간 채우기

        # 체크박스와 콤보박스를 포함하는 레이아웃
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.view_only_measured_checkbox)
        options_layout.addWidget(QLabel("Select Sensor Data Type:"))
        options_layout.addWidget(self.sensor_data_type_combo)
        options_layout.addStretch()

        layout1 = QVBoxLayout()
        layout1.addLayout(top_layout)
        layout1.addWidget(self.progress_widget)  # Run 버튼 위에 추가
        layout1.addLayout(options_layout)  # 체크박스와 콤보박스를 포함하는 레이아웃 추가
        layout1.addLayout(graph_layout)
        layout1.addLayout(self.algoLayout)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

    def changeToggle(self, status):
        if status:
            self.toggleBtn.setText("Step By Step ON")
            self.algoLayout.all_btn.setEnabled(False)
        else:
            self.toggleBtn.setText("Step By Step OFF")
            self.algoLayout.all_btn.setEnabled(True)

    def onCheckboxToggled(self, state):
        self.updateGraph()

    def onSensorDataTypeChanged(self, index):
        self.updateGraph()

    def On_loadDataFile(self):
        fname = QFileDialog.getOpenFileName(self)
        if not fname[0]:
            return
        self.filepath = fname[0]
        self.filenameLabel.setText(fname[0])
        self.loadDatafromFile()

    def loadDatafromFile(self):
        self.loadedData = SensorBinaryFileHandler(self.filepath).load_frames()
        self.updateGraph()

    def updateGraph(self):
        self.makedData = self.makeLoadDatatoGraph(self.loadedData,
                                                  isMeasured=self.view_only_measured_checkbox.isChecked())
        if self.ResimData is not None:
            self.makedData['Resim Weight'] = self.makeResimDatatoGraph(self.ResimData,
                                                                       isMeasured=self.view_only_measured_checkbox.isChecked())
        else:
            if 'Resim Weight' in self.makedData.keys():
                del self.makedData['Resim Weight']

        self.graph_widget.set_data(self.makedData)
        self.mae_graph_widget.set_data(self.makedData, mode='mae')
        self.rmse_graph_widget.set_data(self.makedData, mode='rmse')
        self.error_graph_widget.set_data(self.makedData, mode='error_rate')

        # 센서 데이터 그래프 업데이트
        if self.loadedData is not None:
            # 콤보박스 선택에 따라 적절한 센서 데이터 생성
            is_diff_mode = self.sensor_data_type_combo.currentIndex()
            if is_diff_mode == 1:
                sensor_data = self.makeSensorDiffToGraph(self.loadedData,
                                                         isMeasured=self.view_only_measured_checkbox.isChecked())
                self.sensor_graph_widget.set_title("Sensor diff from Reference Value")
            elif is_diff_mode == 2 or is_diff_mode == 3:
                sensor_data = self.makeSensorFilterToGraph(self.loadedData,
                                                           isMeasured=self.view_only_measured_checkbox.isChecked())
                self.sensor_graph_widget.set_title("Filtered sensor diff (from reference Value)")
            else:
                sensor_data = self.makeSensorDataToGraph(self.loadedData,
                                                         isMeasured=self.view_only_measured_checkbox.isChecked())
                self.sensor_graph_widget.set_title("Sensor Distance Graph")

            self.sensor_graph_widget.set_data(sensor_data)

    def makeResimDatatoGraph(self, data: List[SensorFrame], isMeasured=True):
        algoweight = []
        for frame in data:
            if isMeasured is False or (isMeasured is True and frame.measured):
                algoweight.append(frame.algorithms.predicted_weight)

        return algoweight

    def makeLoadDatatoGraph(self, data: List[SensorFrame], isMeasured=True):
        mdata = dict()
        wlist = []
        algoweight = []
        for frame in data:
            if isMeasured is False or (isMeasured is True and frame.measured):
                wlist.append(sum(frame.experiment.weights))
                algoweight.append(frame.algorithms.predicted_weight)

        mdata['Actual Weights'] = wlist
        mdata['Algorithm Weights'] = algoweight
        return mdata

    def makeSensorDataToGraph(self, data: List[SensorFrame], isMeasured=True):
        # 센서 데이터를 저장할 딕셔너리 초기화
        sensor_dict = {}

        # 첫 번째 프레임의 센서 위치를 사용해 딕셔너리 키 생성
        if data and len(data) > 0:
            first_frame = data[0]
            for sensor in first_frame.sensors:
                location_name = sensor.location.name
                sensor_dict[location_name] = []

        # 각 프레임에서 센서 데이터 추출
        for frame in data:
            if isMeasured is False or (isMeasured is True and frame.measured):
                # 각 센서 위치별로 distance 값 추출
                for sensor in frame.sensors:
                    location_name = sensor.location.name
                    sensor_dict[location_name].append(sensor.distance)

        return sensor_dict

    def makeSensorDiffToGraph(self, data: List[SensorFrame], isMeasured=True):
        # 센서 데이터를 저장할 딕셔너리 초기화
        sensor_dict = {}

        # 첫 번째 프레임의 센서 위치를 사용해 딕셔너리 키 생성
        if data and len(data) > 0:
            first_frame = data[0]
            for sensor in first_frame.sensors:
                location_name = sensor.location.name
                sensor_dict[location_name] = []

        # 각 프레임에서 센서 데이터 추출
        for frame in data:
            # print('refvalue: ',frame.algorithms.referenceValue)
            if isMeasured is False or (isMeasured is True and frame.measured):
                # 각 센서 위치별로 distance 값 추출
                for sensor in frame.sensors:
                    location_name = sensor.location.name
                    # 알고리즘 데이터에 있는 reference 값과 센서 값 차이 계산
                    if frame.algorithms and frame.algorithms.referenceValue:
                        # 각 센서 위치에 맞는 reference 값 인덱스 찾기
                        ref_index = sensor.location.value
                        if ref_index < len(frame.algorithms.referenceValue):
                            ref_value = frame.algorithms.referenceValue[ref_index]
                            if ref_value != 0:
                                diff = ref_value - sensor.distance
                                if ref_index in [1, 3]:
                                    diff *= 0.45
                                sensor_dict[location_name].append(diff)
                        else:
                            # reference 값이 없는 경우 0으로 처리
                            sensor_dict[location_name].append(0)
                    else:
                        # 알고리즘 데이터가 없는 경우 0으로 처리
                        sensor_dict[location_name].append(0)  # print(sensor_dict[location_name])
        return sensor_dict

    def makeSensorFilterToGraph(self, data: List[SensorFrame], isMeasured=True):
        # 센서 데이터를 저장할 딕셔너리 초기화
        sensor_dict = {}
        alpha = 0.2
        window_size = 30
        # 첫 번째 프레임의 센서 위치를 사용해 딕셔너리 키 생성
        if data and len(data) > 0:
            first_frame = data[0]
            for sensor in first_frame.sensors:
                location_name = sensor.location.name
                sensor_dict[location_name] = []

        # 각 프레임에서 센서 데이터 추출
        for frame in data:
            # print('refvalue: ',frame.algorithms.referenceValue)
            if isMeasured is False or (isMeasured is True and frame.measured):
                # 각 센서 위치별로 distance 값 추출
                for sensor in frame.sensors:
                    location_name = sensor.location.name
                    # 알고리즘 데이터에 있는 reference 값과 센서 값 차이 계산
                    if frame.algorithms and frame.algorithms.referenceValue:
                        # 각 센서 위치에 맞는 reference 값 인덱스 찾기
                        ref_index = sensor.location.value
                        if ref_index < len(frame.algorithms.referenceValue):
                            ref_value = frame.algorithms.referenceValue[ref_index]
                            if ref_value != 0:
                                diff = ref_value - sensor.distance
                                if ref_index in [1, 3]:
                                    diff *= 0.45
                                sensor_dict[location_name].append(diff)
                        else:
                            # reference 값이 없는 경우 0으로 처리
                            sensor_dict[location_name].append(0)
                    else:
                        # 알고리즘 데이터가 없는 경우 0으로 처리
                        sensor_dict[location_name].append(0)
        filter_mode = self.sensor_data_type_combo.currentIndex()  # 2: LPF, 3: MAF

        for loc in sensor_dict:
            values = sensor_dict[loc]
            filtered = []

            if filter_mode == 3:
                buf = deque(maxlen=window_size)
                for v in values:
                    buf.append(v)
                    filtered.append(sum(buf) / len(buf))

            else:
                prev = None
                for v in values:
                    if prev is None:
                        filtered.append(v)
                    else:
                        v = alpha * v + (1 - alpha) * prev
                        filtered.append(v)
                    prev = v

            sensor_dict[loc] = filtered

        return sensor_dict

    def updateLabel(self):
        resbuf = self.procmanager.getResultBufs()
        for bname, val in resbuf.items():
            if not val.empty():
                data = val.get()
                print(bname, data)

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
        self.resimulManager.setDataFile(self.filepath)
        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                print('run - ', cbx.text())
                if cbx.text() in self.files:
                    print('select algorithm file -> ', cbx.text(), self.files[cbx.text()])
                    self.resimulManager.addProcess(self.files[cbx.text()])

        self.resimulManager.startThread(callback=self.algoLayout.setBtnforRunAlgorithm,
                                        datacallback=self.setDataProcessed, statuscallback=self.setStatus,
                                        resimcompcallback=self.setResimComp)

    def setResimComp(self, data: List[SensorFrame]):
        self.ResimData = data
        self.updateGraph()

    def setStatus(self, status):
        self.progress_widget.set_status(status)

    def setDataProcessed(self, progress, sf: SensorFrame, legacy_ad: AlgorithmData):
        self.progress_widget.set_value(progress)

    # def setBtnforRunAlgorithm(self):
    #     self.algoLayout.stop_btn.setEnabled(True)
    #     self.algoLayout.start_btn.setEnabled(False)
    #     self.algoLayout.all_btn.setEnabled(False)

    def finishAllAlgorithms(self):
        self.resimulManager.terminateAll()
        self.algoLayout.stop_btn.setEnabled(False)
        self.algoLayout.start_btn.setEnabled(True)
        self.algoLayout.all_btn.setEnabled(True)
