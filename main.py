import sys

from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox
from algorithm_multiproc import AlgorithmMultiProc
from algorithm_multiproc_v2 import AlgorithmMultiProcV2
from algorithm_resimulation import AlgorithmResimulation
from analytics import Analytics
from experiment import Experiment

from arduino_manager import SerialManager
from experiment_v2 import ExperimentTab
from weight_action import WeightTable


def sync_callback(group):
    print("Synchronized group:")
    for data in group:
        print(f"{data.serialport}: (Timestamp: {data.timestamp}, port_index: {data.port_index}, value: {data.value}, sub1: {data.sub1}, sub2: {data.sub2})")
    print("----")

class Main(QWidget):
    def __init__(self):
        super().__init__()
        self._quick_handlers = []
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()

        self.DEBUG_MODE = True

        # self.serial_manager = SerialManager(debug_mode=self.DEBUG_MODE, callback=sync_callback)
        self.serial_manager = SerialManager(debug_mode=self.DEBUG_MODE)
        self.serial_manager.errorSignal.connect(self.showErrorMassage)
        self.serial_manager.start_threads()

        #submit exit handler

        wtEx = WeightTable()
        wtAlgo = WeightTable()

        wtEx.addWeightTable(wtAlgo)
        wtAlgo.addWeightTable(wtEx)

        self.tab0 = ExperimentTab(dataManager=self.serial_manager)
        self.tab1 = Experiment(serial_manager=self.serial_manager, wt=wtEx)
        self.tab2 = AlgorithmMultiProcV2(parent=self, serial_manager=self.serial_manager, wt=wtAlgo)
        self.tab3 = AlgorithmResimulation(serial_manager=self.serial_manager)
        self.tab4 = Analytics()

        self.tabs.addTab(self.tab1, '실험 데이터 수집')
        self.tabs.addTab(self.tab2, '실시간 알고리즘 테스트')
        self.tabs.addTab(self.tab3, '알고리즘 리시뮬레이션')
        self.tabs.addTab(self.tab4, '분석')
        self.tabs.addTab(self.tab0, 'Experiment_V2')

        vbox = QVBoxLayout()
        vbox.addWidget(self.tabs)

        self.setLayout(vbox)

        self.setWindowTitle('화물과적 중심 탄소중립을 위한 데이터 수집 툴')
        self.resize(2000, 800)
        self.show()

    def on_AppExit(self, handler):
        self._quick_handlers.append(handler)

    def _AppExit(self):
        for handler in self._quick_handlers:
            handler()

    def showErrorMassage(self, msg):
        QMessageBox.critical(self, "시리얼 오류", msg)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "종료 확인",
            "프로그램을 종료하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            print("프로그램 종료 중: 시리얼 스레드 정리 등 정리 작업 수행")
            #등록된 모든 핸들러에게 종료 시그널 전송
            self._AppExit()
            if self.serial_manager:
                self.serial_manager.stop_threads()  # 필요한 정리 작업이 있다면 이처럼 호출


            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())