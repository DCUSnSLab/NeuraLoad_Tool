from PyQt5.QtWidgets import QVBoxLayout, QWidget, QTableWidget
import pyqtgraph as pg

from datainfo import SENSORLOCATION


class SensorGraph(QWidget):
    def __init__(self):
        super().__init__()

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

class SensorTable(QWidget):
    def __init__(self):
        super().__init__()

        headers = [
            loc.name.title().replace('_', '')
            for loc in SENSORLOCATION
            if loc is not SENSORLOCATION.NONE
        ]

        self.sensor_table = QTableWidget(1, len(headers))
        self.sensor_table.setHorizontalHeaderLabels(headers)
        self.sensor_table.setVerticalHeaderLabels(['value'])
        self.sensor_table.setMaximumHeight(200)
        self.sensor_table.setMinimumHeight(150)
        self.sensor_table.setMaximumWidth(1000)
        self.sensor_table.setMinimumWidth(500)

        layout = QVBoxLayout()
        layout.addWidget(self.sensor_table)

        self.setLayout(layout)