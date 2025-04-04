from PyQt5.QtCore import QThread, pyqtSignal
import datetime
from arduino_manager import SerialThread
from PyQt5.QtWidgets import QTableWidgetItem

class GUIController(QThread):
    plot_updated = pyqtSignal()
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
                    # print(port,'=> ',data)
                    self.dataUpdate(port, data)
                    # self.loggingUpdate(port, data)
            self.plot_updated.emit()
            self.msleep(1)


    def dataUpdate(self, port, value):
        plot_data = self.guiModule.plot_data[port]
        plot_change = self.guiModule.plot_change[port]

        plot_curve = self.guiModule.plot_curve[port]
        plot_curve_change = self.guiModule.plot_curve_change[port]

        plot_data.append(value)
        plot_change.append(value)

