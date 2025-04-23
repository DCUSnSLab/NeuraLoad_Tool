import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget


class AnalyticsDataGraph(QWidget):
    def __init__(self, x, y, file_name, value):
        super().__init__()
        self.x_value = x
        self.y_value = y
        self.file_name = file_name
        self.loc = value

        self.data_load()

    def data_load(self):
        pass