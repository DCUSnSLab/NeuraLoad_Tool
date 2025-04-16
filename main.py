import sys

from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox
from algorithm_multiproc import AlgorithmMultiProc
from analytics import Analytics
from experiment import Experiment
from algorithm_resimulation import AlgorithmResimulation

from arduino_manager import SerialManager

def sync_callback(group):
    print("Synchronized group:")
    for data in group:
        print(f"{data.serialport}: (Timestamp: {data.timestamp}, port_index: {data.port_index}, value: {data.value}, sub1: {data.sub1}, sub2: {data.sub2})")
    print("----")

class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()

        self.DEBUG_MODE = True

        # self.serial_manager = SerialManager(debug_mode=self.DEBUG_MODE, callback=sync_callback)
        self.serial_manager = SerialManager(debug_mode=self.DEBUG_MODE)
        self.serial_manager.errorSignal.connect(self.showErrorMassage)
        self.serial_manager.start_threads()

        self.tab1 = Experiment(serial_manager=self.serial_manager)
        self.tab2 = AlgorithmMultiProc(serial_manager=self.serial_manager)
        self.tab3 = AlgorithmResimulation(serial_manager=self.serial_manager)
        self.tab4 = Analytics()

        self.tab1.add_subscriber(self.tab2)
        self.tab1.add_subscriber(self.tab3)
        self.tab1.add_subscriber(self.tab4)

        self.tabs.addTab(self.tab1, '실험')
        self.tabs.addTab(self.tab2, '알고리즘')
        self.tabs.addTab(self.tab3, '리시뮬레이션')
        self.tabs.addTab(self.tab4, '분석')

        vbox = QVBoxLayout()
        vbox.addWidget(self.tabs)

        self.setLayout(vbox)

        self.setWindowTitle('화물과적 중심 탄소중립을 위한 데이터 수집 툴')
        self.resize(2000, 800)
        self.show()

    def showErrorMassage(self, msg):
        QMessageBox.critical(self, "시리얼 오류", msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())