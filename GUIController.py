from PyQt5.QtCore import QThread, pyqtSignal


class GUIController(QThread):
    plot_updated = pyqtSignal()

    def __init__(self, GUI, serial_manager, tab_info):
        super(GUIController, self).__init__()
        self.guiModule = GUI
        self.serialManager = serial_manager
        self.tab_info = tab_info

    def run(self):
        print('run GUI Thread')
        while True:
            try:
                group_data = self.serialManager.exper_buffer.get()
                for data in group_data.sensors:
                    self.dataUpdate(data)
                self.plot_updated.emit()
            except Exception as e:
                print("GUIController : ", e)
            # self.msleep(15)

    def dataUpdate(self, data):
        if self.tab_info == 'Experiment':
            plot_data = self.guiModule.plot_data.get(data.serial_port)
            plot_change = self.guiModule.plot_change.get(data.serial_port)
            save_buf = self.guiModule.save_buffer.get(data.serial_port) # 저장 버퍼 가져오기

            plot_curve = self.guiModule.plot_curve[data.serial_port]
            plot_curve_change = self.guiModule.plot_curve_change[data.serial_port]

            plot_data.append(data)
            plot_change.append(data)
            save_buf.append(data) # 저장 버퍼에 데이터 추가

            # print(data.serialport, data.timestamp, data.value, data.port_index)
        elif self.tab_info == 'LaserLightSensor':
            plot_data = self.guiModule.plot_data.get(data.serial_port)

            plot_data.append(data)
