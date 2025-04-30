from PyQt5.QtWidgets import QMainWindow, QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QSplitter
from PyQt5.QtCore import Qt
import pyqtgraph as pg


class AnalyticsGraph(QDockWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.main_window = parent

        self.cb_list = []
        self.plot_items = {}

        self.loc_map = {
            'BOTTOM_RIGHT': 'red',
            'TOP_LEFT': 'green',
            'TOP_RIGHT': 'yellow',
            'BOTTOM_LEFT': 'orange'
        }

        self.graph_widget = pg.PlotWidget()

        self.check_graph_layout = QWidget()
        self.box_layout = QVBoxLayout()
        self.check_graph_layout.setLayout(self.box_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.graph_widget)
        splitter.addWidget(self.check_graph_layout)

        self.setWidget(splitter)

        self.graph_data()

    def graph_data(self):
        for loc, data_line in self.data.items():
            weight_data = []
            value_data = []
            for weight, value in data_line.items():
                weight_data.append(weight)
                value_data.append(value)

            base_loc = '_'.join(loc.split('_')[:2])
            color = self.loc_map.get(base_loc, 'black')

            plot_item = self.graph_widget.plot(weight_data, value_data, pen=pg.mkPen(color='black', width=2), name=loc)

            self.plot_items[loc] = {
                'plot': plot_item,
                'color': color
            }

            self.check_loc(loc)

    def check_loc(self, loc):
        if loc not in [cb.text() for cb in self.cb_list]:
            cb = QCheckBox(loc)
            cb.stateChanged.connect(self.check_graph)
            self.box_layout.addWidget(cb)
            self.cb_list.append(cb)

    def check_graph(self):
        for cb in self.cb_list:
            loc = cb.text()
            if loc in self.plot_items:
                if cb.isChecked():
                    self.plot_items[loc]['plot'].setPen(pg.mkPen(self.plot_items[loc]['color'], width=2))
                else:
                    self.plot_items[loc]['plot'].setPen(pg.mkPen('black', width=2))

    def close_event(self, event):
        event.ignore()
        self.main_window.addDockWidget(Qt.RightDockWidgetArea, self)
        self.setFloating(False)