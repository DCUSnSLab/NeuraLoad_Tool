import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()
        self.setupUI()
        self.setup()

    def initUI(self):
        self.setWindowTitle('과적 테스트')
        self.show()

    def setupUI(self):
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setRowCount(2)
        for i in range(5):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(f'sensor{i+1}'))
        self.table.setVerticalHeaderLabels(['Laser', 'IMU'])
        self.table.setMaximumHeight(135)
        self.table.setMaximumWidth(820)

        self.logging = QLabel('로그 출력')
        self.logging.setStyleSheet("border: 1px solid black; padding: 10px;")
        self.logging.setMinimumHeight(300)

        self.start_btn = QPushButton('시작', self)
        self.start_btn.clicked.connect(self.start)

        self.restart_btn = QPushButton('재시작', self)
        self.restart_btn.clicked.connect(self.restart)

        self.tracking_btn = QPushButton('변화추적', self)
        self.tracking_btn.clicked.connect(self.tracking)

        self.weight_input = QLineEdit()
        self.weight_input.setStyleSheet("background-color: white")

        self.weight_lable = QLabel('Kg')

        self.weight_btn = QPushButton('입력', self)
        self.weight_btn.clicked.connect(self.weight)

        self.save_btn = QPushButton('저장', self)
        self.save_btn.clicked.connect(self.save)

        self.save_file_box_log = QLabel('저장된 파일')

    def start(self):
        pass

    def restart(self):
        pass

    def tracking(self):
        pass

    def weight(self):
        pass

    def save(self):
        pass

    def setup(self):
        weight_input_layout = QHBoxLayout()
        weight_input_layout.addWidget(self.weight_input, alignment=Qt.AlignLeft)
        weight_input_layout.addWidget(self.weight_lable, alignment=Qt.AlignLeft)
        weight_input_layout.addWidget(self.weight_btn, alignment=Qt.AlignLeft)

        weight_box = QGroupBox('무게 입력')
        weight_box.setLayout(weight_input_layout)
        weight_box.setMaximumHeight(100)

        layout_btn1 = QHBoxLayout()
        layout_btn1.addWidget(self.start_btn)
        layout_btn1.addWidget(self.restart_btn)

        save_file_box = QGroupBox('저장된 파일')
        save_file_layout = QHBoxLayout()
        save_file_layout.addWidget(self.save_file_box_log)
        save_file_box.setLayout(save_file_layout)


        layout_btn2 = QVBoxLayout()
        layout_btn2.addLayout(layout_btn1)
        layout_btn2.addWidget(self.tracking_btn)
        layout_btn2.addWidget(weight_box)
        layout_btn2.addWidget(self.save_btn)
        layout_btn2.addWidget(save_file_box)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.logging)
        layout1.addLayout(layout_btn2)

        layout2 = QVBoxLayout()
        layout2.addWidget(self.table)
        layout2.addLayout(layout1)

        self.setLayout(layout2)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = MyApp()
   sys.exit(app.exec_())
