import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout
from algorithm import Algorithm
from experiment import Experiment


class Main(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()

        self.tab1 = Experiment()
        self.tab2 = Algorithm()

        self.tab1.add_subscriber(self.tab2)

        self.tabs.addTab(self.tab1, '실험')
        self.tabs.addTab(self.tab2, '알고리즘')

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