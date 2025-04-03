from PyQt6.QtCore import QThread
import datetime
from arduino_manager import SerialThread
from PyQt5.QtWidgets import QTableWidgetItem

class GUIController(QThread):
    def __init__(self, GUI, serialModules):
        super(GUIController, self).__init__()
        self.guiModule = GUI
        self.serialModules: SerialThread = serialModules

    def run(self):
        print('run GUI Thread')
        while True:
            for module in self.serialModules:
                port = module.port
                if not module.databuf.empty():
                    data = module.databuf.get()
                    #print(port,'=> ',data)
                    self.plotUpdate(port, data)
                    # self.loggingUpdate(port, data)
            self.msleep(1)


    def plotUpdate(self, port, value):
        plot_data = self.guiModule.plot_data[port]
        plot_change = self.guiModule.plot_change[port]

        plot_curve = self.guiModule.plot_curve[port]
        plot_curve_change = self.guiModule.plot_curve_change[port]

        plot_data.append(value)
        plot_change.append(value)

        x = list(range(len(plot_data)))
        y = list(plot_data)

        base_val = plot_change[0] if len(plot_change) > 0 else 0
        change = [v - base_val for v in plot_change]

        plot_curve.setData(x, y)
        plot_curve_change.setData(x, change)

    def loggingUpdate(self, port, value):
        short_time = datetime.datetime.now().strftime("%M_%S_%f")[:-3]
        location = self.port_index[port]
        self.sensor_table.setItem(0, location, QTableWidgetItem(str(value)))

        current_row = self.logging.rowCount()
        self.logging.insertRow(current_row)
        self.logging.setItem(current_row, 0, QTableWidgetItem(short_time))
        self.logging.setItem(current_row, 1, QTableWidgetItem(str(self.weight_a)))
        # self.logging.setItem(current_row, 2, QTableWidgetItem(direction))
        # self.logging.setItem(current_row, 3, QTableWidgetItem(name))
        self.logging.setItem(current_row, 4, QTableWidgetItem(str(value)))
        # self.logging.setItem(current_row, 5, QTableWidgetItem(str(s_value)))
        self.logging.setItem(current_row, 6, QTableWidgetItem(str(self.aaaa)))
        self.logging.scrollToBottom()

