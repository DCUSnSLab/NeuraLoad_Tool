import datetime
import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque

from GUIController import GUIController
from arduino_manager import SerialThread, get_arduino_ports, SerialThreadVirtual


class Experiment(QWidget):
    def __init__(self):
        super().__init__()
        self.DEBUG_MODE = True
        self.threads = []
        self.GUIThread = None
        self.subscribers = []
        self.port_index = {}
        self.weight_a = [0] * 9
        self.count = 0
        self.weight_total = 0
        self.count_t = 't'
        self.last_direction = '-'
        self.is_paused_global = False
        self.aaaa = False
        self.save_graph_max = 500
        self.save_graph_min = 0
        self.port_comboboxes = {}
        self.port_column_index = {}

        self.ports = get_arduino_ports(self.DEBUG_MODE)
        self.port_location = {}
        self.port_colors = {}

        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}

        # self.setting()
        self.setupUI()
        self.setup()
        # self.setup_live_logging()
        self.startSerialThread()
        self.startGUIThread()
        # self.installEventFilter(self)

        # self.auto_save_timer = QTimer()
        # self.auto_save_timer.timeout.connect(self.auto_save)
        # # self.auto_save_timer.start(600000)
        # self.auto_save_timer.start(1000)

        # self.live_log_timer = QTimer()
        # self.live_log_timer.timeout.connect(self.setup_live_logging)
        # self.live_log_timer.start(100000)  # 10분마다 호출 (600,000ms)

        # self.graph_timer = QTimer()
        # self.graph_timer.timeout.connect(self.update_graphs)
        # self.graph_timer.start(100)  # 0.5초마다 그래프만 갱신

    # def update_graphs(self):
    #     for port in self.ports:
    #         x = list(range(len(self.plot_data[port])))
    #         y = list(self.plot_data[port])
    #
    #         if len(self.plot_change[port]) == 0:
    #             continue
    #
    #         base_val = self.plot_change[port][0]
    #         change = [v - base_val for v in self.plot_change[port]]
    #
    #         self.plot_curve[port].setData(x, y)
    #         self.plot_curve_change[port].setData(x, change)

    def add_subscriber(self, subscriber):
        self.subscribers.append(subscriber)

    def broadcast_data(self, port, data):
        for sub in self.subscribers:
            sub.update_data(port, data)

    def broadcast_weight(self):
        for sub in self.subscribers:
            sub.set_weight(self.weight_a)

    # def setting(self):
    #     for i, port in enumerate(self.ports):
    #         if i == 0:
    #             name = 'BottomLeft'
    #             color = 'r'
    #         elif i == 1:
    #             name = 'TopRight'
    #             color = 'g'
    #         elif i == 2:
    #             name = 'TopLeft'
    #             color = 'b'
    #         elif i == 3:
    #             name = 'BottomRight'
    #             color = 'orange'
    #         elif i == 4:
    #             name = 'IMU'
    #             color = 'yellow'
    #         else:
    #             name = 'etc'
    #             color = 'purple'
    #
    #         self.port_location[port] = name
    #         self.port_colors[name] = color

    def setupUI(self):
        self.sensor_table = QTableWidget()
        self.sensor_table.setColumnCount(len(self.ports))
        self.sensor_table.setRowCount(1)
        for i in range(len(self.ports)):
            port = self.ports[i]
            name = self.port_location.get(port, "")
            self.sensor_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
            self.port_index[port] = i
        self.sensor_table.setVerticalHeaderLabels(['value'])
        self.sensor_table.setMaximumHeight(200)
        self.sensor_table.setMinimumHeight(150)
        self.sensor_table.setMaximumWidth(1000)
        self.sensor_table.setMinimumWidth(500)

        # self.logging = QTableWidget()
        # self.logging.setColumnCount(7)
        # self.logging.setHorizontalHeaderLabels(['시간', '무게', '무게 변화', '위치', '로그', '강도', 't/f'])
        # self.logging.setMinimumHeight(150)
        # self.logging.setMinimumWidth(150)
        # self.logging.horizontalHeader().setStretchLastSection(True)

        self.save_file_box_log = QTableWidget()
        self.save_file_box_log.setColumnCount(1)
        self.save_file_box_log.setHorizontalHeaderLabels(['저장된 파일'])
        self.save_file_box_log.setMaximumHeight(500)
        self.save_file_box_log.setMaximumWidth(300)
        self.save_file_box_log.horizontalHeader().setStretchLastSection(True)
        self.save_file_box_log.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.weight_table = QTableWidget(3, 3)
        self.weight_table.setHorizontalHeaderLabels([f"{i + 1}" for i in range(3)])
        self.weight_table.setVerticalHeaderLabels([f"{i + 1}" for i in range(3)])
        self.weight_table.setMaximumHeight(200)
        self.weight_table.setMinimumHeight(150)
        self.weight_table.setMaximumWidth(500)
        self.weight_table.setMinimumWidth(500)
        self.weight_table.installEventFilter(self)
        self.weight_table.cellChanged.connect(self.onCellChanged)

        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(self.weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1

        self.stop_btn = QPushButton('실험 시작', self)
        self.stop_btn.setCheckable(True)
        self.stop_btn.clicked.connect(self.toggle_btn)

        # self.restart_btn = QPushButton('실험 종료', self)
        # self.restart_btn.clicked.connect(self.restart)

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(self.weightP)

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(self.weightM)

        self.weight_btn_z = QPushButton('리셋', self)
        self.weight_btn_z.clicked.connect(self.weightZ)

        # self.save_btn = QPushButton('저장', self)
        # self.save_btn.clicked.connect(self.btn_save)

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("Sensor Change")
        self.graph_change.setLabel("left", "Change")
        self.graph_change.setLabel("bottom", "Time")
        self.graph_change.addLegend(offset=(30, 30))
        self.graph_change.setMinimumWidth(500)

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Sensor")
        self.graph_value.setLabel("left", "Value")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.setMinimumWidth(500)

        # self.log_output = QTextEdit()
        # self.log_output.setReadOnly(True)
        # self.log_output.setStyleSheet("background-color: #F2F2F2;")
        # self.log_output.append(str(self.port_location))

        self.graph_label_max = QLabel('그래프 최대: ')
        self.graph_text_max = QLineEdit()
        self.graph_text_max.returnPressed.connect(self.saveGraphMax)

        self.graph_label_min = QLabel('그래프 최소: ')
        self.graph_text_min = QLineEdit()
        self.graph_text_min.returnPressed.connect(self.saveGraphMin)

        self.port_label_layout = QVBoxLayout()
        self.port_location_selection = {}
        for idx, port in enumerate(self.ports):
            port_label = QLabel(port)
            port_location_cb = QComboBox()
            port_location_cb.addItems([' ', 'BottomLeft', 'TopRight', 'TopLeft', 'BottomRight', 'IMU', 'etc'])
            port_location_cb.adjustSize()

            self.port_comboboxes[port] = port_location_cb
            self.port_column_index[port] = idx

            port_location_cb.currentTextChanged.connect(
                lambda value, p=port: self.update_sensor_table_header(p, value)
            )

            self.port_label_layout.addWidget(port_label)
            self.port_label_layout.addWidget(port_location_cb)

    # def update_sensor_table_header(self, port, new_label):
    #     index = self.port_column_index.get(port)
    #     if index is not None and new_label.strip() != '':
    #         self.sensor_table.setHorizontalHeaderItem(index, QTableWidgetItem(new_label))
    #         print(f"{port} → 센서 테이블 헤더 이름 변경됨: {new_label}")
    #
    #         if port in self.plot_curve:
    #             self.plot_curve[port].setName(new_label)
    #         if port in self.plot_curve_change:
    #             self.plot_curve_change[port].setName(new_label)
    #
    #         self.port_location[port] = new_label

    def update_sensor_table_header(self, port, new_label):
        index = self.port_column_index.get(port)
        if index is None or new_label.strip() == '':
            return

        self.sensor_table.setHorizontalHeaderItem(index, QTableWidgetItem(new_label))
        print(f"{port} → 센서 테이블 헤더 이름 변경됨: {new_label}")
        self.port_location[port] = new_label

        # 기존 그래프 제거
        if port in self.plot_curve:
            self.graph_value.removeItem(self.plot_curve[port])
        if port in self.plot_curve_change:
            self.graph_change.removeItem(self.plot_curve_change[port])

        color = self.port_colors.get(new_label, 'gray')

        # 새로운 그래프 추가 (legend 포함)
        self.plot_curve[port] = self.graph_value.plot(
            pen=pg.mkPen(color=color, width=1),
            name=new_label
        )
        self.plot_curve_change[port] = self.graph_change.plot(
            pen=pg.mkPen(color=color, width=1),
            name=new_label
        )

        self.graph_value.addLegend()
        self.graph_change.addLegend()

    def save_port_location(self, port, new_label):
        index =  self.port_column_index.get(port)
        self.sensor_table.setHorizontalHeaderItem(index, QTableWidgetItem(new_label))
        print(f"{port} → {new_label}")  # 디버깅용 출력

    def saveGraphMax(self):
        text = self.graph_text_max.text().strip()
        self.save_graph_max = int(text)

        self.graph_text_max.clear()
        self.updateGraph()

    def saveGraphMin(self):
        text = self.graph_text_min.text().strip()
        self.save_graph_min = int(text)

        self.graph_text_min.clear()
        self.updateGraph()

    def startSerialThread(self):
        os.makedirs("log", exist_ok=True)
        filename = datetime.datetime.now().strftime("raw_data_%Y-%m-%d.txt")
        self.raw_data_file = open(os.path.join("log", filename), "a", encoding="utf-8")

        for i, port in enumerate(self.ports):
            print('make Serial', i, port)
            if port.startswith('V'):
                thread = SerialThreadVirtual(port, self.ports)
                thread.start()
                self.threads.append(thread)
            else:
                thread = SerialThread(port)
                thread.start()
                self.threads.append(thread)

        location_name = self.port_comboboxes[port].currentText().strip()
        default_color = 'gray'
        self.port_colors = {
            'BottomLeft': 'r',
            'TopRight': 'g',
            'TopLeft': 'b',
            'BottomRight': 'orange',
            'IMU': 'yellow',
            'etc': 'purple'
        }

        color = self.port_colors.get(location_name, default_color)

        for port in self.ports:
            self.plot_data[port] = deque(maxlen=300)
            self.plot_change[port] = deque(maxlen=300)
            # color = self.port_colors.get(self.port_location[port])

            self.plot_curve[port] = self.graph_value.plot()
            self.plot_curve_change[port] = self.graph_change.plot()

            self.plot_curve[port] = self.graph_value.plot(
                pen=pg.mkPen(color=color, width=1),
                name=location_name if location_name else port
            )

            self.plot_curve_change[port] = self.graph_change.plot(
                pen=pg.mkPen(color=color, width=1),
                name=location_name if location_name else port
            )

    def startGUIThread(self):
        print('start GUIThread')
        self.GUIThread = GUIController(self, self.threads)
        self.GUIThread.plot_updated.connect(self.updateGraph)
        self.GUIThread.start()

    def updateGraph(self):
        self.graph_change.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)
        self.graph_value.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)
        short_time = datetime.datetime.now().strftime("%M_%S_%f")[:-3]

        for port in self.ports:
            if self.port_comboboxes[port].currentText().strip() == '':
                continue

            x = list(range(len(self.plot_data[port])))
            # y = list(self.plot_data[port])
            y = [v[1] for v in self.plot_data[port]]

            base_val = self.plot_change[port][0][1] if len(self.plot_change[port]) > 0 else 0
            change = [v[1] - base_val for v in self.plot_change[port]]

            self.plot_curve[port].setData(x, y)
            self.plot_curve_change[port].setData(x, change)

            if self.aaaa:
                value = -1
                data = self.plot_data[port]
                if len(self.plot_data[port]) > 0:
                    value = self.plot_data[port][-1][1]
                location = self.port_index[port]
                self.sensor_table.setItem(0, location, QTableWidgetItem(str(value)))
                self.handle_serial_data(port, data)

            # 로깅 테이블 기록
            # current_row = self.logging.rowCount()
            # self.logging.insertRow(current_row)
            # self.logging.setItem(current_row, 0, QTableWidgetItem(short_time))
            # self.logging.setItem(current_row, 1, QTableWidgetItem(str(self.weight_a)))
            # self.logging.setItem(current_row, 2, QTableWidgetItem("direction"))
            # self.logging.setItem(current_row, 3, QTableWidgetItem("name"))
            # self.logging.setItem(current_row, 4, QTableWidgetItem(str(value)))
            # self.logging.setItem(current_row, 5, QTableWidgetItem("-"))
            # self.logging.setItem(current_row, 6, QTableWidgetItem(str(self.aaaa)))
            # self.logging.scrollToBottom()

    def handle_serial_data(self, port, data):
        if port not in self.port_index:
            return

        # 무게 변화 방향 계산
        total = sum(self.weight_a)
        if total > self.weight_total:
            direction = 'U'
            self.last_direction = direction
        elif total < self.weight_total:
            direction = 'D'
            self.last_direction = direction
        else:
            direction = self.last_direction
        self.weight_total = total

        # 현재 상태 플래그
        state_flag = 't' if self.is_paused_global else 'f'
        name = self.port_location.get(port, port)

        # 데이터 포맷 정리
        if isinstance(data, deque):
            data = list(data)
        if not isinstance(data, list) or len(data) < 2:
            print(f"[경고] 예상치 못한 데이터 형식 또는 길이 부족: {data}")
            return

        last_point = data[-1]
        if not isinstance(last_point, (list, tuple)) or len(last_point) < 2:
            print(f"[경고] 잘못된 포맷: {last_point}")
            return

        timestamp = last_point[0]
        value1 = float(last_point[1])
        value2 = float(last_point[2])
        value3 = float(last_point[3])

        log_line = f"{timestamp}\t{self.weight_a}\t{direction}\t{name}\t{value1}\t{value2}\t{value3}\t{state_flag}\n"
        if hasattr(self, "raw_data_file") and not self.raw_data_file.closed:
            self.raw_data_file.write(log_line)
            self.raw_data_file.flush()

            #
            # # 브로드캐스트
            # self.broadcast_data(port, data)
            #
            # x = list(range(len(self.plot_data[port])))
            # y = list(self.plot_data[port])
            #
            # base_val = self.plot_change[port][0] if len(self.plot_change[port]) > 0 else 0
            # change = [v - base_val for v in self.plot_change[port]]

    def stop(self):
        self.aaaa = True  # 전역 상태 갱신

        QCoreApplication.processEvents()

    def restart(self):
        self.aaaa = False  # 전역 상태 갱신

    def toggle_btn(self):
        if self.stop_btn.isChecked():
            self.aaaa = True
            QCoreApplication.processEvents()
            self.stop_btn.setText("실험 종료")
        else:
            self.aaaa = False
            self.stop_btn.setText("실험 시작")

    def onCellChanged(self, row, col):
        try:
            item = self.weight_table.item(row, col)
            if item is None:
                return

            new_value = item.text().strip()
            index = row * 3 + col

            if 0 <= index < len(self.weight_a):
                try:
                    self.weight_a[index] = int(new_value)
                    self.broadcast_weight()
                except ValueError:
                    prev_value = self.weight_a[index]
                    item.setText(str(prev_value))
            else:
                prev_value = -1
                item.setText(str(prev_value))

        except Exception as e:
            self.log_output.append(f"onCellChanged 오류: {e}")

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
            for val in selected_items:
                try:
                    text = val.text().strip()
                    current_value = int(text)

                    row = val.row()
                    col = val.column()
                    index = row * 3 + col

                    if 0 <= index < len(self.weight_a):
                        if current_value < 4:
                            self.weight_a[index] = 0
                        else:
                            self.weight_a[index] = current_value - 20

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

    def auto_save(self):
        try:
            timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]
            folder_name = datetime.datetime.now().strftime("%Y-%m-%d")
            print("auto on")
            self.save(timestamp, folder_name)
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"오류 발생: {e}", QMessageBox.Ok)

    def btn_save(self):
        try:
            timestamp = datetime.datetime.now().strftime("save_%H_%M_%S_%f")[:-3]
            folder_name = datetime.datetime.now().strftime("saved_data_%Y-%m-%d")
            self.save(timestamp, folder_name)
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"오류 발생: {e}", QMessageBox.Ok)

    def save(self, timestamp, folder_name):
        file_name = f"{timestamp}.txt"
        folder_path = os.path.join("log", folder_name)

        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, file_name)

        with open(file_path, 'w', encoding='utf-8') as file:
            for row in range(self.logging.rowCount()):
                print(self.logging.item(row, 5).text())
                current_time = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]

                weight = self.logging.item(row, 0).text() if self.logging.item(row, 0) else ""

                weight_change = self.logging.item(row, 1).text() if self.logging.item(row, 1) else ""

                port = self.logging.item(row, 2).text() if self.logging.item(row, 2) else ""

                log_data = self.logging.item(row, 3).text() if self.logging.item(row, 3) else ""
                log_content = ",".join(log_data.split(','))
                etc = self.logging.item(row, 4).text() if self.logging.item(row, 4) else ""
                s_etc = self.logging.item(row, 5).text() if self.logging.item(row, 5) else ""
                T_F = self.logging.item(row, 6).text() if self.logging.item(row, 6) else ""
                # 파일에 기록
                file.write(f"{current_time}\t{weight}\t{weight_change}\t{port}\t{log_content}\t{etc}\t{s_etc}\t{T_F}\n")

        row_position = self.save_file_box_log.rowCount()
        self.save_file_box_log.insertRow(row_position)
        self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(file_name))
        self.save_file_box_log.scrollToBottom()

    # def setup_live_logging(self):
    #     # 로그 디렉토리
    #     folder_name = "log"
    #     os.makedirs(folder_name, exist_ok=True)
    #
    #     # 파일명: 날짜별 파일 하나만 계속 사용
    #     filename = datetime.datetime.now().strftime("raw_data_%Y-%m-%d.txt")
    #     file_path = os.path.join(folder_name, filename)
    #     print("auto on3")
    #     # 이미 열려 있다면 무시하고, 없으면 새로 열기 (append 모드)
    #     if not hasattr(self, "live_log_file") or self.live_log_file.closed or self.live_log_file.name != file_path:
    #         # 이전 파일 닫기
    #         if hasattr(self, "live_log_file") and not self.live_log_file.closed:
    #             self.live_log_file.close()
    #         print("auto on")
    #         self.live_log_file = open(file_path, "a", encoding="utf-8")
    #
    #         # 헤더가 없으면 한 번만 쓰기 (선택)
    #         if os.stat(file_path).st_size == 0:
    #             self.live_log_file.write("시간\t무게\t무게 변화\t포트\t로그\t상태\n")
    #             self.live_log_file.flush()
    #
    #         # UI에 파일명 추가 (중복 방지)
    #         row_position = self.save_file_box_log.rowCount()
    #         if all(self.save_file_box_log.item(row, 0).text() != filename for row in
    #                range(self.save_file_box_log.rowCount())):
    #             print("auto on2")
    #             self.save_file_box_log.insertRow(row_position)
    #             self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(filename))
    #             self.save_file_box_log.scrollToBottom()

    def setup(self):
        graph_max_layout = QHBoxLayout()
        graph_max_layout.addWidget(self.graph_label_max)
        graph_max_layout.addWidget(self.graph_text_max)

        graph_min_layout = QHBoxLayout()
        graph_min_layout.addWidget(self.graph_label_min)
        graph_min_layout.addWidget(self.graph_text_min)

        setting_layout = QVBoxLayout()
        setting_layout.addLayout(graph_max_layout)
        setting_layout.addLayout(graph_min_layout)
        setting_layout.addLayout(self.port_label_layout)

        weight_input_layout2 = QHBoxLayout()
        weight_input_layout2.addWidget(self.weight_btn_p)
        weight_input_layout2.addWidget(self.weight_btn_m)

        layout_btn1 = QHBoxLayout()
        layout_btn1.addWidget(self.stop_btn)
        # layout_btn1.addWidget(self.restart_btn)

        layout_btn2 = QVBoxLayout()
        layout_btn2.addLayout(weight_input_layout2)
        layout_btn2.addWidget(self.weight_btn_z)
        layout_btn2.addLayout(layout_btn1)
        # layout_btn2.addWidget(self.save_btn)
        layout_btn2.addWidget(self.save_file_box_log)

        layout1 = QHBoxLayout()
        # layout1.addWidget(self.logging)
        layout1.addWidget(self.sensor_table)
        layout1.addLayout(layout_btn2)

        table_layout = QHBoxLayout()
        # table_layout.addWidget(self.sensor_table)
        table_layout.addLayout(setting_layout)
        table_layout.addWidget(self.weight_table)

        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graph_change)
        graph_layout.addWidget(self.graph_value)
        # graph_layout.addWidget(self.log_output)

        layout2 = QVBoxLayout()
        layout2.addLayout(table_layout)
        layout2.addLayout(layout1)

        layout3 = QHBoxLayout()
        layout3.addLayout(layout2)
        layout3.addLayout(graph_layout)

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
        if hasattr(self, "raw_data_file") and not self.raw_data_file.closed:
            self.raw_data_file.close()

        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Experiment()
   sys.exit(app.exec_())