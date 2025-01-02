import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from datetime import datetime

class SerialThread(QThread):
    # 시그널 생성
    data_received = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port # 포트
        self.baudrate = baudrate # 보트레이트
        self.is_running = True # 쓰레드 실행 상태
        self.is_paused = False # 쓰레드 일시 중지 상태
        self.list_data = []
        self.data_all = []

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print("연결되었습니다.")

            while self.is_running:
                if self.is_paused:
                    QThread.msleep(100)
                    continue

                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8').strip()
                    self.data_received.emit(data) # 시그널 방출, 함수에 데이터 전달
                    self.list_data = data.split(',')
                    self.data_all.append(self.list_data)

        except serial.SerialException as e:
            print(f"오류: {e}")

    def pause(self):
        self.is_paused = True
        print("데이터 통신 일시 중지")

    def resume(self):
        self.ser.flushInput()
        self.is_paused = False
        print("데이터 통신 재시작")

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.weight_text = "0"
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
        self.logging.setColumnCount(2)
        self.logging.setHorizontalHeaderLabels(['무게', '로그'])
        self.logging.setMinimumHeight(300)
        self.logging.setMinimumWidth(500)
        self.logging.horizontalHeader().setStretchLastSection(True)

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
        self.weight_input.returnPressed.connect(self.weight)

        self.save_btn = QPushButton('저장', self)
        self.save_btn.clicked.connect(self.save)

        self.save_file_box_log = QTableWidget()
        self.save_file_box_log.setColumnCount(1)
        self.save_file_box_log.setHorizontalHeaderLabels(['저장된 파일'])
        self.save_file_box_log.setMinimumHeight(100)
        self.save_file_box_log.setMinimumWidth(300)
        self.save_file_box_log.horizontalHeader().setStretchLastSection(True)
        self.save_file_box_log.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)

    def startSerialThread(self):
        self.serial_thread = SerialThread('COM6', 9600)
        self.serial_thread.data_received.connect(self.handle_serial_data)
        self.serial_thread.start()

    def handle_serial_data(self, data):
        if len(data) >= 3:
            current_row_count = self.logging.rowCount()
            self.logging.insertRow(current_row_count)

            self.logging.setItem(current_row_count, 0, QTableWidgetItem(self.weight_text))
            self.logging.setItem(current_row_count, 1, QTableWidgetItem(data))

        self.data = self.serial_thread.list_data
        if len(self.data) >= 4:
            #값은 z, x, y로 들어감
            self.table.setItem(0, 0, QTableWidgetItem(self.data[0]))
            self.table.setItem(1, 0, QTableWidgetItem(self.data[-1]))
            self.table.setItem(2, 0, QTableWidgetItem(self.data[-2]))
            self.table.setItem(3, 0, QTableWidgetItem(self.data[-3]))

    def stop(self):
        self.serial_thread.pause()

    def restart(self):
        self.serial_thread.resume()

    def tracking(self):
        pass

    def weight(self):
        self.weight_text = self.weight_input.text().strip()
        if self.weight_text:
            current_row_count = self.logging.rowCount()
            self.logging.setItem(current_row_count, 0, QTableWidgetItem(f"{self.weight_text}"))
            print(f"무게 추가: {self.weight_text}")

    def save(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{timestamp}.txt"

            with open(file_name, 'w', encoding='utf-8') as file:
                row_count = self.logging.rowCount()
                column_count = self.logging.columnCount()

                headers = [self.logging.horizontalHeaderItem(c).text() for c in range(column_count)]
                file.write("\t".join(headers) + "\n")

                for row in range(row_count):
                    row_data = [
                        self.logging.item(row, col).text() if self.logging.item(row, col) else ""
                        for col in range(column_count)
                    ]
                    file.write("\t".join(row_data) + "\n")

            row_position = self.save_file_box_log.rowCount()
            self.save_file_box_log.insertRow(row_position)
            self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(file_name))
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"오류 발생: {str(e)}", QMessageBox.Ok)

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

        layout_btn2 = QVBoxLayout()
        layout_btn2.addLayout(layout_btn1)
        layout_btn2.addWidget(self.tracking_btn)
        layout_btn2.addWidget(weight_box)
        layout_btn2.addWidget(self.save_btn)
        layout_btn2.addWidget(self.save_file_box_log)

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