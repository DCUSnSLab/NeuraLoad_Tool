import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from datetime import datetime
import pyqtgraph as pg
from collections import deque
import serial.serialutil
import os
import numpy as np
# 무게 추정
from Estimation_mass_algorithm import LaserDataProcessor

class SerialThread(QThread):
    data_received = pyqtSignal(str, str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port # 포트
        self.baudrate = baudrate # 보트레이트
        self.is_running = True # 쓰레드 실행 상태
        self.is_paused = False # 쓰레드 일시 중지 상태

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            while self.is_running:
                if self.is_paused:
                    QThread.msleep(100)
                    continue
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    self.data_received.emit(self.port, data) # 시그널 방출, 함수에 데이터 전달
        except serial.serialutil.SerialException as e:
            print(f"오류: {e}")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.ser.flushInput()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()

class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        self.changes = {}

        self.laser_changes = {port: deque(maxlen=300) for port in ['COM9', 'COM10', 'COM8', 'COM11']}
        self.prev_laser_values = {port: None for port in ['COM9', 'COM10', 'COM8', 'COM11']}

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

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(600000)

    def initUI(self):
        self.setWindowTitle('과적 테스트')
        self.resize(2000, 800)
        self.show()

    def setupUI(self):
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setRowCount(4)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('TopLeft'))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem('BottomLeft'))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem('TopRight'))
        self.table.setHorizontalHeaderItem(3, QTableWidgetItem('BottomRight'))

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

        self.stop_btn = QPushButton('정지(K)', self)
        self.stop_btn.clicked.connect(self.stop)

        self.restart_btn = QPushButton('재시작(L)', self)
        self.restart_btn.clicked.connect(self.restart)

        self.weight_btn_p = QPushButton('+(P)', self)
        self.weight_btn_p.clicked.connect(self.weightP)

        self.weight_btn_m = QPushButton('-(O)', self)
        self.weight_btn_m.clicked.connect(self.weightM)

        self.weight_btn_z = QPushButton('리셋(I)', self)
        self.weight_btn_z.clicked.connect(self.weightZ)

        self.save_btn = QPushButton('저장(M)', self)
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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)

        self.main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()

        self.graphWidgets = {}
        self.curves = {}

        self.port_colors = {
            'COM9': 'r',
            'COM10': 'b',
            'COM8': 'g',
            'COM11': 'orange'
        }

        sensor_titles = ["Laser"]

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Laser Change")
        self.graph_value.setLabel("left", "Change")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.addLegend(offset=(30, 30))

        self.curves["Laser Change"] = {}

        for port, color in self.port_colors.items():
            if color == 'r':
                curve = self.graph_value.plot(pen=color, name="TopLeft")
            elif color == 'b':
                curve = self.graph_value.plot(pen=color, name="BottomLeft")
            elif color == 'g':
                curve = self.graph_value.plot(pen=color, name="TopRight")
            elif color == 'orange':
                curve = self.graph_value.plot(pen=color, name="BottomRight")
            else:
                pass
            self.curves["Laser Change"][port] = curve

        self.left_layout.addWidget(self.graph_value)

        for sensor in sensor_titles:
            graph = pg.PlotWidget()
            graph.setTitle(sensor)
            graph.setLabel("left", "Value")
            graph.setLabel("bottom", "Time")

            self.graphWidgets[sensor] = graph

            self.curves[sensor] = {}

            for port, color in self.port_colors.items():
                curve = graph.plot(pen=color)
                self.curves[sensor][port] = curve

            self.left_layout.addWidget(graph)

    def PredictedWeight(self):
        laser_processor = LaserDataProcessor()

        for port in ["COM9", "COM10", "COM8", "COM11"]:
            if len(self.laser_changes[port]) == 0:
                print(f"[경고] {port}에 대한 변화량 데이터 없음")
                self.laser_changes[port].append(0)

            self.changes[port] = self.laser_changes[port][-1]
            print(f"{port}의 마지막 변화량: {self.changes[port]}")

        laser_processor.process_data(0, self.changes["COM9"])
        laser_processor.process_data(1, self.changes["COM10"])
        laser_processor.process_data(2, self.changes["COM8"])
        laser_processor.process_data(3, self.changes["COM11"])

        closest_indices = laser_processor.process_data(0, self.changes["COM9"])
        print(f"계산된 가장 가까운 인덱스: {closest_indices}")  # 가장 가까운 인덱스 출력

        # 우선순위에 따라 category를 선택
        for category in ["left", "mid", "right"]:
            print(f"카테고리 확인 중: {category}")  # 현재 확인 중인 카테고리 출력
            if category in closest_indices and closest_indices[category] is not None:
                weight_value = closest_indices[category]
                detected_category = category.upper()  # "LEFT", "MID", "RIGHT"
                print(f"선택된 카테고리: {detected_category}, 값: {weight_value}")  # 선택된 카테고리와 값 출력
                break  # 우선순위가 먼저 선택된 category로 결정되면 반복문 종료

        # if weight_value == -1:
        #     print("[경고] 적절한 값이 없으므로 반환합니다.")  # 값이 없을 때 경고 출력
        #     return  # 적절한 값이 없다면 반환

        # QLabel이 삭제되지 않았는지 확인 후 텍스트 변경
        if hasattr(self, 'weight_value_label') and self.weight_value_label:
            print(f"예상 무게 텍스트 업데이트: {weight_value} KG")  # 예상 무게 텍스트 업데이트 출력
            self.weight_value_label.setText(f"예상 무게 결과: {weight_value} KG")
        else:
            self.weight_value_label = QLabel(f"예상 무게 결과: {weight_value} KG")
            font = self.weight_value_label.font()
            font.setBold(True)
            font.setPointSize(30)
            self.weight_value_label.setFont(font)
            self.left_layout.addWidget(self.weight_value_label)

        if hasattr(self, 'category_label') and self.category_label:
            print(f"감지된 위치 텍스트 업데이트: {detected_category}")  # 감지된 위치 텍스트 업데이트 출력
            self.category_label.setText(f"감지된 위치: {detected_category}")
        else:
            self.category_label = QLabel(f"감지된 위치: {detected_category}")
            font = self.category_label.font()
            font.setBold(True)
            font.setPointSize(20)
            self.category_label.setFont(font)
            self.left_layout.addWidget(self.category_label)

    def startSerialThread(self):
        self.data_x = {port: deque(maxlen=300) for port in self.port_colors}
        self.data_y = {
            "Laser": {port: deque(maxlen=300) for port in self.port_colors},
            "IMU[x]": {port: deque(maxlen=300) for port in self.port_colors},
            "IMU[y]": {port: deque(maxlen=300) for port in self.port_colors},
            "IMU[z]": {port: deque(maxlen=300) for port in self.port_colors},
        }

        ports = list(self.port_colors.keys())
        for port in ports:
            thread = SerialThread(port, 9600)
            thread.data_received.connect(self.handle_serial_data)
            self.threads.append(thread)
            thread.start()

    def handle_serial_data(self, port, data):
        parsed_data = data.split(',')

        # 데이터가 12개 미만이면 처리하지 않음
        if 1 < len(parsed_data) < 12:
            return

        try:
            sensor_data = [int(x) if x.isdigit() else 0 for x in parsed_data]
        except ValueError:
            return

        if not self.data_x[port]:
            self.data_x[port].append(0)
        else:
            self.data_x[port].append(self.data_x[port][-1] + 1)

        self.data_y["Laser"][port].append(sensor_data[0])  # Laser 데이터 추가

        # IMU 데이터가 있을 때만 처리
        if len(sensor_data) > 12:
            self.data_y["IMU[x]"][port].append(sensor_data[-3])
            self.data_y["IMU[y]"][port].append(sensor_data[-1])
            self.data_y["IMU[z]"][port].append(sensor_data[-2])
        if sensor_data[0] == 0:
            return
        # 변화량 계산
        if self.prev_laser_values[port] is None:
            self.prev_laser_values[port] = sensor_data[0]
            print(f"포트 {port}: 초기값 설정됨, 현재 값: {sensor_data[0]}")
            change = 0  # 초기값일 경우 변화량 0
        else:
            # if sensor_data[0] != 0:  # sensor_data[0]이 0이 아닐 경우에만 초기값 설정
            print(f"포트 {port}: 이전 값: {self.prev_laser_values[port]}, 현재 값: {sensor_data[0]}")
            change = self.prev_laser_values[port] - sensor_data[0]  # 변화량 계산

        self.laser_changes[port].append(change)

        # 변화량 계산 후 prev_laser_values는 업데이트하지 않음
        # self.prev_laser_values[port] = sensor_data[0]  # 이전 값 갱신 제거

        port_index = list(self.port_colors.keys()).index(port)
        self.table.setItem(0, port_index, QTableWidgetItem(str(sensor_data[0])))  # Laser
        if len(sensor_data)>12:
            self.table.setItem(1, port_index, QTableWidgetItem(str(sensor_data[-3])))  # IMU[x]
            self.table.setItem(2, port_index, QTableWidgetItem(str(sensor_data[-1])))  # IMU[y]
            self.table.setItem(3, port_index, QTableWidgetItem(str(sensor_data[-2])))  # IMU[z])

        self.PredictedWeight()

        for sensor in ["Laser"]:
            x_data = list(self.data_x[port])
            y_data = list(self.data_y[sensor][port])

            min_length = min(len(x_data), len(y_data))
            if min_length > 0:
                self.curves[sensor][port].setData(x_data[-min_length:], y_data[-min_length:])

            # Laser Change 그래프 업데이트
        x_data = list(self.data_x[port])
        y_data = list(self.laser_changes[port])

        min_length = min(len(x_data), len(y_data))
        if min_length > 0:
            self.curves["Laser Change"][port].setData(x_data[-min_length:], y_data[-min_length:])

        current_row_count = self.logging.rowCount()
        self.logging.insertRow(current_row_count)
        self.logging.setItem(current_row_count, 0, QTableWidgetItem(str(self.weight_a)))
        if port == 'COM9':
            name = "TopLeft"
        elif port == 'COM10':
            name = "BottomLeft"
        elif port == 'COM8':
            name = "TopRight"
        elif port == 'COM11':
            name = "BottomRight"
        else:
            name = ""
            print("지정된 이외의 포트가 있음")

        self.logging.setItem(current_row_count, 1, QTableWidgetItem(name))
        self.logging.setItem(current_row_count, 2, QTableWidgetItem(data))

        self.logging.scrollToBottom()

    def stop(self):
        for thread in self.threads:
            thread.pause()
        QCoreApplication.processEvents()

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
                    self.weight_a[index] = (current_value + 20)
                    val.setText(str(self.weight_a[index]))
                except ValueError:
                    continue

    def weightM(self):
        selected_items = self.weight_table.selectedItems()
        if selected_items:
            # 선택된 항목의 개수가 1개인 경우와 13개인 경우를 구분하여 처리
            if len(selected_items) == 1:
                # 1개의 값만 선택된 경우
                val = selected_items[0]
                try:
                    current_value = int(val.text())

                    row = val.row()
                    col = val.column()
                    index = row * 3 + col  # 3x3 배열로 인덱스 계산

                    if current_value < 4:
                        self.weight_a[index] = 0
                        val.setText(str(self.weight_a[index]))
                    else:
                        self.weight_a[index] = (current_value - 20)
                        val.setText(str(self.weight_a[index]))
                except ValueError:
                    pass  # 예외 발생 시 처리하지 않고 넘어감

            elif len(selected_items) == 13:
                # 13개의 값이 선택된 경우
                for val in selected_items:
                    try:
                        current_value = int(val.text())

                        row = val.row()
                        col = val.column()
                        index = row * 3 + col

                        if current_value < 4:
                            self.weight_a[index] = 0
                            val.setText(str(self.weight_a[index]))
                        else:
                            self.weight_a[index] = (current_value - 20)
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
        try:
            item = self.weight_table.item(row, col)
            if item is None:
                return

            new_value = item.text().strip()
            index = row * 3 + col

            # 인덱스가 유효한지 확인하고 값 변경
            if 0 <= index < len(self.weight_a):
                try:
                    self.weight_a[index] = int(new_value)
                except ValueError:
                    prev_value = self.weight_a[index]  # 기존 값을 가져옴
                    item.setText(str(prev_value))
            else:
                prev_value = -1
                item.setText(str(prev_value))

        except Exception as e:
            print(f"onCellChanged 오류: {e}")

    def save(self):
        try:
            timestamp = datetime.now().strftime("%H_%M_%S_%f")[:-3]
            file_name = f"{timestamp}.txt"

            folder_name = datetime.now().strftime("saved_data_%Y-%m-%d")
            folder_path = os.path.join("log", folder_name)
            os.makedirs(folder_path, exist_ok=True)

            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'w', encoding='utf-8') as file:
                    headers = ['Logged Time', '무게', '포트', '로그']
                    file.write("\t".join(headers) + "\n")

                    for row in range(self.logging.rowCount()):
                        weight = self.logging.item(row, 0).text() if self.logging.item(row, 0) else ""

                        port = self.logging.item(row, 1).text() if self.logging.item(row, 1) else ""

                        if port == 'COM9':
                            name = "TopLeft"
                        elif port == 'COM10':
                            name = "BottomLeft"
                        elif port == 'COM8':
                            name = "TopRight"
                        elif port == 'COM11':
                            name = "BottomRight"
                        else:
                            name = ""
                            print("지정된 이외의 포트가 있음")

                        log_data = self.logging.item(row, 2).text() if self.logging.item(row, 2) else ""
                        log_content = ",".join(log_data.split(','))

                        current_time = datetime.now().strftime("%H_%M_%S_%f")[:-3]

                        file.write(f"{current_time}\t{weight}\t{name}\t{log_content}\n")

            row_position = self.save_file_box_log.rowCount()
            self.save_file_box_log.insertRow(row_position)
            self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(file_name))
            self.save_file_box_log.scrollToBottom()

        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"오류 발생: {e}", QMessageBox.Ok)

    def auto_save(self):
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            folder_path = os.path.join("log", date_str)
            os.makedirs(folder_path, exist_ok=True)  # 폴더 없으면 생성

            # 파일 이름 생성 (HHMMSS.txt)
            time_str = datetime.now().strftime("%H_%M_%S_%f")[:-3]
            file_name = f"{time_str}.txt"
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'w', encoding='utf-8') as file:
                headers = ['Logged Time', '무게', '포트', '로그']
                file.write("\t".join(headers) + "\n")

                row_count = self.logging.rowCount()
                for row in range(row_count):
                    log_data = self.logging.item(row, 2).text() if self.logging.item(row, 2) else ""
                    parsed_data = log_data.split(',')

                    logged_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]

                    weight = self.logging.item(row, 0).text() if self.logging.item(row, 0) else ""

                    port = self.logging.item(row, 1).text() if self.logging.item(row, 1) else ""

                    if port == 'COM9':
                        name = "TopLeft"
                    elif port == 'COM10':
                        name = "BottomLeft"
                    elif port == 'COM8':
                        name = "TopRight"
                    elif port == 'COM11':
                        name = "BottomRight"
                    else:
                        name = ""
                        print("지정된 이외의 포트가 있음")

                    log_content = ",".join(parsed_data) if parsed_data else ""

                    file.write(f"{logged_time}\t{weight}\t{name}\t{log_content}\n")

            # 저장된 파일을 UI에 추가
            row_position = self.save_file_box_log.rowCount()
            self.save_file_box_log.insertRow(row_position)
            self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(file_path))
            self.save_file_box_log.scrollToBottom()

        except Exception as e:
            print(f"Error while saving: {e}")

    def update_table(self):
        if self.current_row < len(self.data):
            row_data = self.data[self.current_row]
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(row_data))
            self.current_row += 1
        else:
            self.timer.stop()

    def restart_arduino(self):
        for thread in self.threads:
            if hasattr(thread, 'ser') and thread.ser.is_open:
                thread.ser.dtr = False
                QThread.msleep(100)
                thread.ser.dtr = True

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

        table_layout = QHBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addWidget(self.weight_table)

        layout2 = QVBoxLayout()
        layout2.addLayout(table_layout)
        layout2.addLayout(layout1)

        layout3 = QHBoxLayout()
        layout3.addLayout(layout2)
        layout3.addLayout(self.left_layout, stretch=3)
        self.setLayout(layout3)

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()

            function_keys = {
                Qt.Key_P: self.weightP,
                Qt.Key_O: self.weightM,
                Qt.Key_I: self.weightZ,
                Qt.Key_M: self.save,
                Qt.Key_K: self.stop,
                Qt.Key_L: self.restart
            }

            if key in function_keys:
                function_keys[key]()
                return True

            key_to_cell = {
                Qt.Key_Q: (0, 0), Qt.Key_W: (0, 1), Qt.Key_E: (0, 2),
                Qt.Key_A: (1, 0), Qt.Key_S: (1, 1), Qt.Key_D: (1, 2),
                Qt.Key_Z: (2, 0), Qt.Key_X: (2, 1), Qt.Key_C: (2, 2)
            }

            if key in key_to_cell:
                row, col = key_to_cell[key]
                self.weight_table.setFocus()
                self.weight_table.setCurrentCell(row, col)
                return True

            if key in [Qt.Key_Return, Qt.Key_Enter]:
                self.weight_table.clearFocus()
                self.setFocus()
                return True

        return super().eventFilter(source, event)

    def closeEvent(self, event):
        for thread in self.threads:
            thread.stop()
        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = MyApp()
   sys.exit(app.exec_())
