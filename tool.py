import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from datetime import datetime
import pyqtgraph as pg

class SerialThread(QThread):
    data_received = pyqtSignal(str, str)

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

            while self.is_running:
                if self.is_paused:
                    QThread.msleep(100)
                    continue

                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8').strip()
                    self.data_received.emit(self.port, data) # 시그널 방출, 함수에 데이터 전달
                    self.list_data = data.split(',')
                    self.data_all.append(self.list_data)

        except serial.SerialException as e:
            print(f"오류: {e}")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.ser.flushInput()
        self.is_paused = False

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.threads = []
        self.weight_text = "0"
        self.current_row = 0
        self.weight_a = [0] * 9
        self.count = 0
        self.initUI()
        self.setupUI()
        self.setup()
        self.startSerialThread()

        self.installEventFilter(self)

    def initUI(self):
        self.setWindowTitle('과적 테스트')
        self.resize(2000, 800)
        self.show()

    def setupUI(self):
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setRowCount(4)
        for i in range(5):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(f'sensor{i+1}'))
        self.table.setVerticalHeaderLabels(['Laser', 'IMU[x]', 'IMU[y]', 'IMU[z]'])
        self.table.setMaximumHeight(300)
        self.table.setMinimumHeight(250)
        self.table.setMaximumWidth(1000)
        self.table.setMinimumWidth(700)

        self.logging = QTableWidget()
        self.logging.setColumnCount(3)
        self.logging.setHorizontalHeaderLabels(['무게', '포트', '로그'])
        self.logging.setMinimumHeight(300)
        self.logging.setMinimumWidth(500)
        self.logging.horizontalHeader().setStretchLastSection(True)

        self.stop_btn = QPushButton('정지', self)
        self.stop_btn.clicked.connect(self.stop)

        self.restart_btn = QPushButton('재시작', self)
        self.restart_btn.clicked.connect(self.restart)

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(self.weightP)

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(self.weightM)

        self.weight_btn_z = QPushButton('리셋', self)
        self.weight_btn_z.clicked.connect(self.weightZ)

        self.save_btn = QPushButton('저장', self)
        self.save_btn.clicked.connect(self.save)

        self.save_file_box_log = QTableWidget()
        self.save_file_box_log.setColumnCount(1)
        self.save_file_box_log.setHorizontalHeaderLabels(['저장된 파일'])
        self.save_file_box_log.setMaximumHeight(500)
        self.save_file_box_log.setMaximumWidth(300)
        self.save_file_box_log.horizontalHeader().setStretchLastSection(True)
        self.save_file_box_log.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.weight_table = QTableWidget(3,3)
        self.weight_table.setHorizontalHeaderLabels([f"{i + 1}" for i in range(3)])
        self.weight_table.setVerticalHeaderLabels([f"{i + 1}" for i in range(3)])
        self.weight_table.setMaximumHeight(300)
        self.weight_table.setMinimumHeight(250)
        self.weight_table.setMaximumWidth(1000)
        self.weight_table.setMinimumWidth(500)
        self.weight_table.installEventFilter(self)
        self.weight_table.cellChanged.connect(self.onCellChanged)

        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(self.weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1

        self.graph1 = pg.PlotWidget()
        self.graph1.setTitle("Laser")
        self.graph1.setLabel("bottom", "Time")

        self.graph2 = pg.PlotWidget()
        self.graph2.setTitle("IMU[x]")
        self.graph2.setLabel("bottom", "Time")

        self.graph3 = pg.PlotWidget()
        self.graph3.setTitle("IMU[y]")
        self.graph3.setLabel("bottom", "Time")

        self.graph4 = pg.PlotWidget()
        self.graph4.setTitle("IMU[z]")
        self.graph4.setLabel("bottom", "Time")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)

    def startSerialThread(self):
        ports = ['COM3', 'COM6', 'COM7', 'COM8']  # 실제 연결된 포트로 변경
        for port in ports:
            thread = SerialThread(port, 9600)
            thread.data_received.connect(self.handle_serial_data)
            self.threads.append(thread)
            thread.start()

    def handle_serial_data(self, port, data):
        parsed_data = data.split(',')

        if len(parsed_data) >= 6:
            sensor_data = parsed_data[1:]

            current_row_count = self.logging.rowCount()
            self.logging.insertRow(current_row_count)
            self.logging.setItem(current_row_count, 0, QTableWidgetItem(str(self.weight_a)))
            self.logging.setItem(current_row_count, 1, QTableWidgetItem(port))
            self.logging.setItem(current_row_count, 2, QTableWidgetItem(data))

            # 값은 z, x, y로 들어감
            if port == 'COM3':
                self.table.setItem(0, 0, QTableWidgetItem(sensor_data[0]))
                self.table.setItem(1, 0, QTableWidgetItem(sensor_data[-2]))
                self.table.setItem(2, 0, QTableWidgetItem(sensor_data[-1]))
                self.table.setItem(3, 0, QTableWidgetItem(sensor_data[-3]))

            elif port == 'COM6':
                self.table.setItem(0, 1, QTableWidgetItem(sensor_data[0]))
                self.table.setItem(1, 1, QTableWidgetItem(sensor_data[-2]))
                self.table.setItem(2, 1, QTableWidgetItem(sensor_data[-1]))
                self.table.setItem(3, 1, QTableWidgetItem(sensor_data[-3]))
            elif port == 'COM7':
                self.table.setItem(0, 2, QTableWidgetItem(sensor_data[0]))
                self.table.setItem(1, 2, QTableWidgetItem(sensor_data[-2]))
                self.table.setItem(2, 2, QTableWidgetItem(sensor_data[-1]))
                self.table.setItem(3, 2, QTableWidgetItem(sensor_data[-3]))
            elif port == 'COM8':
                self.table.setItem(0, 3, QTableWidgetItem(sensor_data[0]))
                self.table.setItem(1, 3, QTableWidgetItem(sensor_data[-2]))
                self.table.setItem(2, 3, QTableWidgetItem(sensor_data[-1]))
                self.table.setItem(3, 3, QTableWidgetItem(sensor_data[-3]))

    def stop(self):
        for thread in self.threads:
            thread.pause()

    def restart(self):
        for thread in self.threads:
            thread.resume()

    def weightP(self):
        selected_items = self.weight_table.selectedItems()
        if selected_items:
            for val in selected_items:
                try:
                    current_value = int(val.text())

                    row = val.row()
                    col = val.column()

                    index = row * 3 + col
                    self.weight_a[index] = (current_value + 5)
                    val.setText(str(self.weight_a[index]))
                except ValueError:
                    continue

    def weightM(self):
        selected_items = self.weight_table.selectedItems()
        if selected_items:
            for val in selected_items:
                try:
                    current_value = int(val.text())

                    row = val.row()
                    col = val.column()
                    index = row * 3 + col

                    if current_value  < 4:
                        self.weight_a[index] = 0
                        val.setText(str(self.weight_a[index]))
                    else:
                        self.weight_a[index] = (current_value - 5)
                        val.setText(str(self.weight_a[index]))
                except ValueError:
                    continue

    def weightZ(self):
        self.weight_a = [0] * 9
        self.count = 0
        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(self.weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1

    def onCellChanged(self, row, col):
        new_value = self.weight_table.item(row, col).text()
        self.weight_a[row * 3 + col] = int(new_value) if new_value else 0

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_P:
                self.weightP()
                return True
            elif event.key() == Qt.Key_M:
                self.weightM()
                return True
            elif event.key() == Qt.Key_Z:
                self.weightZ()
                return True
        return super().eventFilter(source, event)

    def save(self):
        try:
            # 파일 이름 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{timestamp}.txt"

            with open(file_name, 'w', encoding='utf-8') as file:
                headers = ['Logged Time', '무게', '포트', '로그']
                file.write("\t".join(headers) + "\n")

                row_count = self.logging.rowCount()
                for row in range(row_count):
                    log_data = self.logging.item(row, 2).text() if self.logging.item(row, 2) else ""
                    parsed_data = log_data.split(',')

                    logged_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    weight = self.logging.item(row, 0).text() if self.logging.item(row, 0) else ""
                    port = self.logging.item(row, 1).text() if self.logging.item(row, 1) else ""
                    log_content = ",".join(parsed_data[1:]) if len(parsed_data) > 1 else ""

                    file.write(f"{logged_time}\t{weight}\t{port}\t{log_content}\n")

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

        weight_input_layout2 = QHBoxLayout()
        weight_input_layout2.addWidget(self.weight_btn_p)
        weight_input_layout2.addWidget(self.weight_btn_m)

        layout_btn1 = QHBoxLayout()
        layout_btn1.addWidget(self.stop_btn)
        layout_btn1.addWidget(self.restart_btn)

        layout_btn2 = QVBoxLayout()
        layout_btn2.addLayout(weight_input_layout2)
        layout_btn2.addWidget(self.weight_btn_z)
        layout_btn2.addLayout(layout_btn1)
        layout_btn2.addWidget(self.save_btn)
        layout_btn2.addWidget(self.save_file_box_log)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.logging)
        layout1.addLayout(layout_btn2)

        graph1 = QHBoxLayout()
        graph1.addWidget(self.graph1)
        graph1.addWidget(self.graph2)

        graph2 = QHBoxLayout()
        graph2.addWidget(self.graph3)
        graph2.addWidget(self.graph4)

        graph3 = QVBoxLayout()
        graph3.addLayout(graph1)
        graph3.addLayout(graph2)

        table_layout = QHBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addWidget(self.weight_table)

        layout2 = QVBoxLayout()
        layout2.addLayout(table_layout)
        layout2.addLayout(layout1)

        layout3 = QHBoxLayout()
        layout3.addLayout(layout2)
        layout3.addLayout(graph3)

        self.setLayout(layout3)

    def closeEvent(self, event):
        for thread in self.threads:
            thread.stop()
        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = MyApp()
   sys.exit(app.exec_())