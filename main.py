import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout
from algorithm import Algorithm
from algorithm_multiproc import AlgorithmMultiProc
from analytics import Analytics
from experiment import Experiment

from arduino_manager import SerialManager

def sync_callback(group):
    print("Synchronized group:")
    for port, record in group.items():
        print(f"{port}: {record}")
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
        self.serial_manager.start_threads()

        self.tab1 = Experiment(serial_manager=self.serial_manager)
        self.tab2 = AlgorithmMultiProc(serial_manager=self.serial_manager)
        self.tab3 = Analytics()

        self.tab1.add_subscriber(self.tab2)
        self.tab1.add_subscriber(self.tab3)

        self.tabs.addTab(self.tab1, '실험')
        self.tabs.addTab(self.tab2, '알고리즘')
        self.tabs.addTab(self.tab3, '분석')

        vbox = QVBoxLayout()
        vbox.addWidget(self.tabs)

        self.setLayout(vbox)

        self.setWindowTitle('화물과적 중심 탄소중립을 위한 데이터 수집 툴')
        self.resize(2000, 800)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())