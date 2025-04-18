from PyQt5.QtCore import QThread, pyqtSignal


class GUIController(QThread):
    plot_updated = pyqtSignal()
    def __init__(self, GUI, serial_manager):
        super(GUIController, self).__init__()
        self.guiModule = GUI
        self.serialManager = serial_manager

    def run(self):
        print('run GUI Thread')
        while True:
            try:
                group_data = self.serialManager.exper_buffer.get()
                for data in group_data:
                    self.dataUpdate(data)
                self.plot_updated.emit()
            except Exception as e:
                print("GUIController : ", e)
            # self.msleep(15)


    def dataUpdate(self, data):
        plot_data = self.guiModule.plot_data.get(data.serialport)
        plot_change = self.guiModule.plot_change.get(data.serialport)

        plot_curve = self.guiModule.plot_curve[data.serialport]
        plot_curve_change = self.guiModule.plot_curve_change[data.serialport]

        plot_data.append(data)
        plot_change.append(data)
        # print(data.serialport, data.timestamp, data.value, data.port_index)