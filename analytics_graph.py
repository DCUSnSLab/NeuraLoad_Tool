from PyQt5.QtWidgets import QMainWindow, QDockWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg

class AnalyticsGraph(QDockWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data

        self.graph_widget = pg.PlotWidget()
        self.setWidget(self.graph_widget)

        self.graph_data()

    def graph_data(self):
        for loc, data_line in self.data.items():
            weight_data = []
            value_data = []
            for weight, value in data_line.items():
                weight_data.append(weight)
                value_data.append(value)

            self.graph_widget.plot(weight_data, value_data, name=loc)