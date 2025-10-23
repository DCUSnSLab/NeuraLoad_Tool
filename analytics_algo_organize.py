from typing import List

from PyQt5.QtWidgets import *

from GUI_MAEGraph import BarGraphWidget
from GUI_graph_NR import GraphWidget
from datainfo import SensorFrame, SensorBinaryFileHandler


class AnalyticsAlgoOrganize(QWidget):
    def __init__(self, file_name):
        super().__init__()
        self.file_name = file_name
        self.load_data = None
        self.ResimData = None

        self.open_file()
        self.graph_init()
        self.update_graph()

    def open_file(self):
        for i in range(len(self.file_name)):
            self.load_data = SensorBinaryFileHandler(self.file_name[i]).load_frames()

    def data_select(self, load_data, isMeasured=True):
        mdata = dict()
        real_weight = []
        algo_weight = []
        for data in load_data:
            if isMeasured is False or (isMeasured is True and data.measured):
                real_weight.append(sum(data.experiment.weights))
                algo_weight.append(data.algorithms.predicted_weight)

        mdata['Actual Weights'] = real_weight
        mdata['Algorithm Weights'] = algo_weight
        return mdata

    def graph_init(self):
        self.view_only_measured_checkbox = QCheckBox("View Only Measured Data")
        self.view_only_measured_checkbox.setChecked(True)
        self.view_only_measured_checkbox.stateChanged.connect(self.onCheckboxToggled)

        self.graph_widget = GraphWidget(title="Algorithm Output Graph")
        self.mae_graph_widget = BarGraphWidget(title="MAE Comparison")
        self.rmse_graph_widget = BarGraphWidget(title="RMSE Comparison")
        self.error_graph_widget = BarGraphWidget(title="Error Rate Comparison")

        graph_layout = QHBoxLayout()
        graph_layout.addWidget(self.graph_widget, stretch=7)
        graph_layout.addWidget(self.mae_graph_widget, stretch=1)
        graph_layout.addWidget(self.rmse_graph_widget, stretch=1)
        graph_layout.addWidget(self.error_graph_widget, stretch=1)

        layout1 = QVBoxLayout()
        layout1.addWidget(self.view_only_measured_checkbox)
        layout1.addLayout(graph_layout)

        self.setLayout(layout1)

    def onCheckboxToggled(self, state):
        self.update_graph()

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

    def update_graph(self):
        self.makedData = self.makeSensorDataToGraph(self.load_data,
                                                    isMeasured=self.view_only_measured_checkbox.isChecked())
        if self.ResimData is not None:
            sensor_data = self.makeSensorDataToGraph(self.load_data,
                                                     isMeasured=self.view_only_measured_checkbox.isChecked())
        else:
            if 'Resim Weight' in self.makedData.keys():
                del self.makedData['Resim Weight']

        self.graph_widget.set_data(self.makedData)
        self.mae_graph_widget.set_data(self.makedData, mode='mae')
        self.rmse_graph_widget.set_data(self.makedData, mode='rmse')
        self.error_graph_widget.set_data(self.makedData, mode='error_rate')
