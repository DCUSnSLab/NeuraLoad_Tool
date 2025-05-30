from PyQt5.QtWidgets import *
from tensorboard.notebook import display

from GUI_MAEGraph import BarGraphWidget
from GUI_graph_NR import GraphWidget
from datainfo import SensorBinaryFileHandler


class AnalyticsAlgoOrganize(QWidget):
    def __init__(self, file_data):
        super().__init__()
        self.file_name = file_data
        self.load_data = None
        self.ResimData = None

        self.graph_init()
        self.open_file()

    def open_file(self):
        self.makedData = {}
        self.load_data_map = {}

        for file in self.file_name:
            data = SensorBinaryFileHandler(file).load_frames()
            file_label = file.split('/')[-1]
            self.load_data_map[file_label] = data

        self.update_graph()

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

    def onCheckboxToggled(self):
        self.update_graph()

    def update_graph(self):
        is_measured = self.view_only_measured_checkbox.isChecked()
        self.makedData.clear()

        for file_label, data in self.load_data_map.items():
            selected = self.data_select(data, isMeasured=is_measured)
            self.makedData['Resim Weight'] = self.data_select(self.ResimData, selected)

        self.graph_widget.set_data(self.makedData)
        self.mae_graph_widget.set_data(self.makedData, mode='mae')
        self.rmse_graph_widget.set_data(self.makedData, mode='rmse')
        self.error_graph_widget.set_data(self.makedData, mode='error_rate')
