import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class SerialThread(QThread):
    # 시그널 생성
    data_received = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port # 포트
        self.baudrate = baudrate # 보트레이트
        self.is_running = True # 쓰레드 실행 상태
        self.list_data = []

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print("연결되었습니다.")

            while self.is_running:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8').strip()
                    self.data_received.emit(data) # 시그널 방출, 함수에 데이터 전달
                    self.list_data = data.split(',')

        except serial.SerialException as e:
            print(f"오류: {e}")

    def stop(self):
        self.is_running = False
        self.ser.close()
        self.quit()

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.current_row = 0
        self.initUI()
        self.setupUI()
        self.setup()
        self.startSerialThread()

    def initUI(self):
        self.setWindowTitle('과적 테스트')
        self.resize(900, 800)
        self.show()

    def setupUI(self):
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setRowCount(4)
        for i in range(5):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(f'sensor{i+1}'))
        self.table.setVerticalHeaderLabels(['Laser', 'IMU[x]', 'IMU[y]', 'IMU[z]'])
        self.table.setMaximumHeight(225)
        self.table.setMaximumWidth(825)

        self.logging = QTableWidget()
        self.logging.setColumnCount(1)
        self.logging.setHorizontalHeaderLabels(['로그 출력'])
        self.logging.setColumnWidth(0, 500)
        self.logging.setMinimumHeight(300)
        self.logging.setMinimumWidth(500)

        self.stop_btn = QPushButton('정지', self)
        self.stop_btn.clicked.connect(self.stop)

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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)

    def startSerialThread(self):
        self.serial_thread = SerialThread('COM3', 9600)
        self.serial_thread.data_received.connect(self.handle_serial_data)
        self.serial_thread.start()

    def handle_serial_data(self, data):
        self.logging.insertRow(self.logging.rowCount())
        self.logging.setItem(self.logging.rowCount() - 1, 0, QTableWidgetItem(data))
        self.data = self.serial_thread.list_data

        if len(self.data) == 4:
            #값은 z, x, y로 들어감
            self.table.setItem(0, 0, QTableWidgetItem(self.data[0]))
            self.table.setItem(1, 0, QTableWidgetItem(self.data[-1]))
            self.table.setItem(2, 0, QTableWidgetItem(self.data[-2]))
            self.table.setItem(3, 0, QTableWidgetItem(self.data[-3]))

    def stop(self):
        print("데이터 통신 일시 중지")

    def restart(self):
        print("데이터 통신 재시작")

    def tracking(self):
        pass

    def weight(self):
        pass

    def save(self):
        pass

    def update_table(self):
        if self.current_row < len(self.data):
            row_data = self.data[self.current_row]
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(row_data))
            self.current_row += 1
        else:
            self.timer.stop()

    def setup(self):
        weight_input_layout1 = QHBoxLayout()
        weight_input_layout1.addWidget(self.weight_input, alignment=Qt.AlignLeft)
        weight_input_layout1.addWidget(self.weight_lable, alignment=Qt.AlignLeft)

        weight_input_layout2 = QHBoxLayout()
        weight_input_layout2.addLayout(weight_input_layout1)
        weight_input_layout2.addWidget(self.weight_btn, alignment=Qt.AlignLeft)

        weight_box = QGroupBox('무게 입력')
        weight_box.setLayout(weight_input_layout2)
        weight_box.setMaximumHeight(100)

        layout_btn1 = QHBoxLayout()
        layout_btn1.addWidget(self.stop_btn)
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

    def closeEvent(self, event):
        self.serial_thread.stop()
        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = MyApp()
   sys.exit(app.exec_())
