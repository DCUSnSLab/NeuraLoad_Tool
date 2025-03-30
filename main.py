import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout
from experiment import Experiment

class Main(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        tab1 = QWidget()
        tab1_layout = QVBoxLayout()
        tab1_layout.addWidget(Experiment())
        tab1.setLayout(tab1_layout)

        tab2 = QWidget()
        # tab2_layout = QVBoxLayout()
        # tab2_layout.addWidget()
        # tab2.setLayout(tab2_layout)

        tab3 = QWidget()
        # tab3_layout = QVBoxLayout()
        # tab3_layout.addWidget()
        # tab3.setLayout(tab3_layout)

        tabs = QTabWidget()
        tabs.addTab(tab1, '실험')
        tabs.addTab(tab2, '알고리즘')
        tabs.addTab(tab3, '분석')

        vbox = QVBoxLayout()
        vbox.addWidget(tabs)

        self.setLayout(vbox)

        self.setWindowTitle('화물과적 중심 탄소중립을 위한 데이터 수집 툴')
        self.resize(2000, 800)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())