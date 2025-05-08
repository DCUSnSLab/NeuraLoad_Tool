from PyQt5.QtWidgets import *
from queue import Queue

from GUI_MAEGraph import BarGraphWidget
from GUI_graph_NR import GraphWidget
from datainfo import SensorBinaryFileHandler


class AnalyticsAlgoOrganize(QWidget):
    def __init__(self, file_name):
        super().__init__()
        self.file_name = file_name

        self.buffer = {}

        self.open_file()

    def open_file(self):
        for i in range(len(self.file_name)):
            self.buffer.clear()
            load_data = SensorBinaryFileHandler(self.file_name[i]).load_frames()
            self.data_select(load_data)

            self.graph_init()

    def data_select(self, load_data):
        self.buffer['real'] = Queue()
        for data in load_data:
            weight = data.experiment.weights
            weight_total = sum(weight)

            algo_name = data.algorithms.algo_type.name
            predicted_weight = data.algorithms.predicted_weight

            buffer_name = algo_name

            if buffer_name not in self.buffer:
                self.buffer[buffer_name] = Queue()

            self.buffer['real'].put(weight_total)
            self.buffer[buffer_name].put(predicted_weight)

    def graph_init(self):
        self.algo_map = {
            'COGMassEstimation' : 'red',
            'COGPositionMassEstimation_v2' : 'green'
        }

        self.graph_widget = GraphWidget(title="Algorithm Output Graph")
        self.mae_graph_widget = BarGraphWidget(title="MAE Comparison")
        self.rmse_graph_widget = BarGraphWidget(title="RMSE Comparison")
        self.error_graph_widget = BarGraphWidget(title="Error Rate Comparison")

        graph_layout = QHBoxLayout()
        graph_layout.addWidget(self.graph_widget, stretch=7)
        graph_layout.addWidget(self.mae_graph_widget, stretch=1)
        graph_layout.addWidget(self.rmse_graph_widget, stretch=1)
        graph_layout.addWidget(self.error_graph_widget, stretch=1)

        self.setLayout(graph_layout)