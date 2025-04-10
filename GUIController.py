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
            candidate = self.serialManager.candidate_window
            if candidate and len(candidate) == len(self.serialManager.ports):
                for port, data in candidate.items():
                    self.dataUpdate(port, data)
            self.plot_updated.emit()
            self.msleep(15)


    def dataUpdate(self, port, data):
        """
                data는 딕셔너리 형태:
                  {
                    "timestamp": "22_18_09_834",
                    "value": 419,
                    "sub1": 431,
                    "sub2": 420,
                    "Data_port_number": "VCOM1",
                    "timestamp_dt": datetime.datetime(...)
                  }

            sensor change 그래프 0으로 바뀌는 현상 수정해야함

            """

        plot_data = self.guiModule.plot_data.get(port)
        plot_change = self.guiModule.plot_change.get(port)

        if plot_data is not None:
            # 기존에는 모듈의 raw 데이터를 append하던 부분 대신, 동기화된 데이터의 tuple을 추가합니다.
            plot_data.append((data["timestamp"], data["value"], data["sub1"], data["sub2"]))
        if plot_change is not None:
            plot_change.append((data["timestamp"], data["value"], data["sub1"], data["sub2"]))