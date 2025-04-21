import datetime
import os
import sys
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from GUIController import GUIController
import traceback
from datainfo import SENSORLOCATION
from weight_action import WeightTable


class Experiment(QWidget):
    def __init__(self, serial_manager, wt):
        super().__init__()
        # weigt Table
        self.weight_table = wt
        self.serial_manager = serial_manager
        self.GUIThread = None
        self.subscribers = []
        self.port_index = {}
        self.weight_a = [-1] * 9
        self.count = 0
        self.weight_total = 0
        self.last_direction = '-'
        self.is_paused_global = True
        self.is_experiment_active = False
        self.save_graph_max = 500
        self.save_graph_min = 0
        self.port_actual_distances = {}
        self.is_syncing = False
        self.port_comboboxes = {}
        self.port_column_index = {}
        self.port_location = {}
        self.port_colors = {
            'TopLeft': 'b',
            'BottomLeft': 'r',
            'TopRight': 'g',
            'BottomRight': 'orange',
            'IMU': 'yellow',
            'etc': 'purple'
        }
        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}

        # 정렬된 ports 사용
        self.ports = [sensor.port for sensor in self.serial_manager.sensors]
        self.port_index = {
            sensor.port: sensor.sensorLoc.value
            for sensor in self.serial_manager.sensors
        }

        self.setupUI()
        self.setup()

        # 딕셔너리 초기화
        self.initializePortData()
        self.startGUIThread()

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(1000)

    def add_subscriber(self, subscriber):
        self.subscribers.append(subscriber)

    def broadcast_data(self, port, data):
        for sub in self.subscribers:
            sub.update_data(port, data)

    def broadcast_weight(self):
        for sub in self.subscribers:
            # 각 subscriber가 set_weight 메소드를 가지고 있는지 확인
            if hasattr(sub, 'set_weight'):
                sub.set_weight(self.weight_a)

    def setupUI(self):
        headers = [
            loc.name.title().replace('_', '')
            for loc in SENSORLOCATION
            if loc is not SENSORLOCATION.NONE
        ]
        self.sensor_table = QTableWidget(1, len(headers))
        self.sensor_table.setHorizontalHeaderLabels(headers)
        self.sensor_table.setVerticalHeaderLabels(['value'])
        self.sensor_table.setMaximumHeight(200)
        self.sensor_table.setMinimumHeight(150)
        self.sensor_table.setMaximumWidth(1000)
        self.sensor_table.setMinimumWidth(500)


        self.stop_btn = QPushButton('실험 시작', self)
        self.stop_btn.setCheckable(True)
        self.stop_btn.clicked.connect(self.toggle_btn)

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(lambda: self.weight_update(True))

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(lambda: self.weight_update(False))

        self.weight_btn_init = QPushButton('init', self)
        # self.weight_btn_init.clicked.connect(self.weight_init)

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("Sensor Change")
        self.graph_change.setLabel("left", "Change")
        self.graph_change.setLabel("bottom", "Time")
        self.graph_change.addLegend(offset=(30, 30))
        self.graph_change.setMinimumWidth(500)

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Sensor Value")
        self.graph_value.setLabel("left", "Value")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.addLegend(offset=(30, 30))
        self.graph_value.setMinimumWidth(500)

        self.graph_label_max = QLabel('그래프 최대: ')
        self.graph_text_max = QLineEdit()
        self.graph_text_max.returnPressed.connect(self.saveGraphMax)

        self.graph_label_min = QLabel('그래프 최소: ')
        self.graph_text_min = QLineEdit()
        self.graph_text_min.returnPressed.connect(self.saveGraphMin)

        # SENSORLOCATION에 정의된 순서대로 정렬(TOP_LEFT, BOTTOM_LEFT, TOP_RIGHT, BOTTOM_RIGHT)
        self.port_label_layout = QVBoxLayout()
        for port in self.ports:
            port_label = QLabel(port)

            cmb = QComboBox()
            cmb.addItems(headers)
            # 기본 선택: port_index[port] 로 설정
            cmb.setCurrentIndex(self.port_index[port])

            # 콤보 박스 변경 시 호출
            cmb.currentTextChanged.connect(
                lambda new_loc, p=port, hdrs=headers:(
                    self.port_index.__setitem__(p, hdrs.index(new_loc)),
                    self.update_sensor_graph(p, new_loc)
                )
            )
            # 거리 입력창
            distance_input = QLineEdit()
            distance_input.returnPressed.connect(
                lambda _, p=port, b=distance_input: self.update_graph_start(p, b.text())
            )
            unit = QLabel('mm')
            row = QHBoxLayout()
            row.addWidget(port_label)
            row.addWidget(cmb)
            row.addWidget(distance_input)
            row.addWidget(unit)
            self.port_label_layout.addLayout(row)

            self.port_comboboxes[port] = cmb

        self.all_weight_text = QLabel("Actual distance")
        self.all_weight_output = QLabel("-")
        self.all_weight_unit = QLabel('kg')

        self.weight_position = QLabel("Weight position")
        self.weight_position_output = QLabel("-")

    def update_sensor_graph(self, port: str, new_label: str):
        """
        콤보 박스 변경 시 그래프 업데이트
        """
        # 기존 그래프 제거
        if port in self.plot_curve:
            self.graph_value.removeItem(self.plot_curve[port])
            self.graph_change.removeItem(self.plot_curve_change[port])

        # 새로운 그래프 추가 (legend 포함)
        color = self.port_colors.get(new_label, 'gray')
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

    def weight_update_text(self):
        weight = sum(self.weight_a)
        if weight == 0:
            self.all_weight_output.setText("0")
        else:
            self.all_weight_output.setText(str(weight))

        weight_location = [0]* 9
        for i in range(len(self.weight_a)):
            if self.weight_a[i] > 0:
                weight_location[i] = 1
        all_weight_location = [i for i in weight_location]

        one_indices = [i+1 for i, val in enumerate(all_weight_location) if val == 1]

        if sum(one_indices) == 0:
            self.weight_position_output.setText("0")
        else:
            self.weight_position_output.setText(str(one_indices))

    def update_graph_start(self, port, value):
        self.port_actual_distances[port] = value
        print(f"{port}의 그래프 초기값 {value}로 설정")

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

    def initializePortData(self):
        # SerialManager의 포트 정보를 기반으로 데이터 딕셔너리 초기화
        for port in self.ports:
            # 이미 초기화된 포트는 건너뛰기
            if port in self.plot_data:
                continue

            self.plot_data[port] = deque(maxlen=300)
            self.plot_change[port] = deque(maxlen=300)

            # 기본 색상 설정
            default_color = 'gray'
            location_name = self.port_comboboxes[port].currentText().strip() if port in self.port_comboboxes else ''
            color = self.port_colors.get(location_name, default_color)

            # 그래프 요소 초기화
            self.plot_curve[port] = self.graph_value.plot(
                pen=pg.mkPen(color=color, width=2),  # 선 두께 증가
                name=location_name if location_name else port
            )

            self.plot_curve_change[port] = self.graph_change.plot(
                pen=pg.mkPen(color=color, width=2),  # 선 두께 증가
                name=location_name if location_name else port
            )

            print(f"포트 초기화 완료: {port}")

    def startGUIThread(self):
        print('start GUIThread')
        # 쓰레드에 SerialManager의 쓰레드도 전달
        self.GUIThread = GUIController(self, self.serial_manager)
        self.GUIThread.plot_updated.connect(self.updateGraph)
        self.GUIThread.start()

    def updateGraph(self, port=None):
        try:
            # 그래프 Y축 범위 설정
            self.graph_change.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)
            self.graph_value.getPlotItem().setYRange(min=0, max=800)

            # 특정 포트만 업데이트하거나 모든 포트 업데이트
            ports_to_update = [port] if port else self.ports

            for port in ports_to_update:
                # 포트가 plot_data에 초기화되어 있지 않으면 초기화
                if port not in self.plot_data:
                    self.plot_data[port] = deque(maxlen=300)
                    self.plot_change[port] = deque(maxlen=300)

                    # 그래프 요소도 없으면 초기화
                    if port not in self.plot_curve:
                        default_color = 'gray'
                        location_name = self.port_comboboxes[
                            port].currentText().strip() if port in self.port_comboboxes else ''
                        color = self.port_colors.get(location_name, default_color)

                        self.plot_curve[port] = self.graph_value.plot(
                            pen=pg.mkPen(color=color, width=2),  # 선 두께 증가
                            name=location_name if location_name else port
                        )

                        self.plot_curve_change[port] = self.graph_change.plot(
                            pen=pg.mkPen(color=color, width=2),  # 선 두께 증가
                            name=location_name if location_name else port
                        )

                # 위치가 설정되지 않은 포트는 건너뛰기
                location_name = self.port_comboboxes[port].currentText().strip() if port in self.port_comboboxes else ''
                if location_name == '':
                    continue

                # 데이터가 없으면 그래프 업데이트 건너뛰기
                if not self.plot_data[port] or len(self.plot_data[port]) == 0:
                    continue

                # X축 데이터 생성 - 시간에 따른 인덱스
                x = list(range(len(self.plot_data[port])))

                # Y축 데이터 추출 - 안전 처리
                y_values = []
                for point in self.plot_data[port]:
                    try:
                        y_value = float(point.distance)
                        y_values.append(y_value)
                    except (ValueError, AttributeError):
                        y_values.append(0)

                # 변화량 데이터 계산
                change_values = []
                if len(self.plot_change[port]) > 0:
                    base_val = None
                    for point in self.plot_change[port]:
                        try:
                            base_val = float(point.distance)
                            break
                        except (ValueError, AttributeError):
                            pass

                    base_input = self.port_actual_distances.get(port)
                    if base_input is None:
                        base_val = 0
                    else:
                        base_val = float(base_input)

                    for point in self.plot_change[port]:
                        try:
                            value = float(point.distance)
                            change_values.append(value - base_val)
                        except (ValueError, AttributeError):
                            change_values.append(0)

                # 데이터가 준비되면 그래프 업데이트
                if len(y_values) > 0 and len(x) == len(y_values):
                    self.plot_curve[port].setData(x, y_values)

                if len(change_values) > 0 and len(x) == len(change_values):
                    self.plot_curve_change[port].setData(x, change_values)

                # 실험 중일 때만 데이터 처리 및 테이블 업데이트
                if self.is_experiment_active:
                    for port in self.ports:
                        val = float(self.plot_data[port][-1].distance)
                        col = self.port_index[port]
                        self.sensor_table.setItem(0, col, QTableWidgetItem(str(val)))

                    # 데이터 저장 처리
                    self.handle_serial_data(port, self.plot_data[port])
        except Exception as e:
            print(f"그래프 업데이트 중 오류 발생: {e}")
            traceback.print_exc()

    def handle_serial_data(self, port, data):
        if port not in self.port_index:
            return

        # data가 비어있는지 확인
        if not data:
            # 디버그 수준을 낮추기 위해 경고 출력 생략
            # print(f"[정보] {port}에 대한 데이터가 아직 없습니다.")
            return

        os.makedirs("log", exist_ok=True)
        filename = datetime.datetime.now().strftime("sensor_data_%Y-%m-%d.bin")
        file_path = os.path.join("log", filename)

        # 무게 변화 방향
        total = sum(self.weight_a)
        if total > self.weight_total:
            direction_byte = b'U';
            self.last_direction = 'U'
        elif total < self.weight_total:
            direction_byte = b'D';
            self.last_direction = 'D'
        else:
            direction_byte = self.last_direction.encode() if isinstance(self.last_direction, str) else b'N'
        self.weight_total = total

        state_flag = b'f' if self.is_paused_global else b't'
        name = self.port_location.get(port, port)

        # data 가 deque 면 list 로 변환
        if isinstance(data, deque):
            data = list(data)
        if not isinstance(data, list) or len(data) < 1:
            print(f"[경고] 예상치 못한 데이터 형식 또는 길이 부족: {data}")
            return
        try:
            latest_point = data[-1]

            timestamp_str = latest_point.timestamp.strftime("%H%M%S%f")[:-3]
            timestamp_int = int(timestamp_str)

            value1 = float(latest_point.distance)
            value2 = float(latest_point.intensity)
            value3 = float(latest_point.temperature)

            weight_bin = struct.pack('<9h', *self.weight_a)
            name_bytes = name.encode('utf-8')[:16]
            name_bin = name_bytes + b'\x00' * (16 - len(name_bytes))
            values_bin = struct.pack('<fff', value1, value2, value3)
            record = struct.pack('<I', timestamp_int) + weight_bin + direction_byte + name_bin + values_bin + state_flag

            with open(file_path, 'ab') as f:
                f.write(record)
        except Exception as e:
            print(f"[오류] 데이터 처리 중 예외 발생: {e}")

    def stop(self):
        self.is_experiment_active = True  # 전역 상태 갱신

        QCoreApplication.processEvents()

    def restart(self):
        self.is_experiment_active = False  # 전역 상태 갱신

    def toggle_btn(self):
        if self.stop_btn.isChecked():
            self.is_experiment_active = True
            self.is_paused_global = False
            self.countdown_value = 5
            
            # 내부 함수로 countdown 정의
            def countdown():
                if self.countdown_value > 0:
                    self.stop_btn.setText(f"{self.countdown_value}초 남음")
                    self.countdown_value -= 1
                    QTimer.singleShot(1000, countdown)
                else:
                    # 5초 후: 실험 종료 상태로 변경
                    self.stop_btn.setChecked(False)  # 버튼 체크 해제
                    self.is_experiment_active = False
                    self.is_paused_global = True
                    self.stop_btn.setText("실험 시작")

            countdown()  # 카운트다운 시작
            QCoreApplication.processEvents()
        else:
            self.is_experiment_active = False
            self.is_paused_global = True
            self.stop_btn.setText("실험 시작")

    def set_weight(self, weight_a):
        if self.is_syncing:
            return

        self.is_syncing = True

        self.weight_a = weight_a.copy()
        self.weight_table.blockSignals(True)
        self.table_update(weight_a)
        self.weight_table.blockSignals(False)

        self.is_syncing = False

        # def weightZ(self):
    #     self.weight_a = [0] * 9
    #     self.count = 0
    #     for row in range(3):
    #         for col in range(3):
    #             val = QTableWidgetItem(str(self.weight_a[self.count]))
    #             val.setTextAlignment(Qt.AlignCenter)
    #             self.weight_table.setItem(row, col, val)
    #             self.count += 1
    #     self.weight_update_text()

    def auto_save(self):
        os.makedirs("log", exist_ok=True)
        filename = datetime.datetime.now().strftime("raw_data_%Y-%m-%d.bin")
        file_path = os.path.join("log", filename)
        with open(file_path, "ab") as f:
            for port in self.ports:
                if port not in self.port_index:
                    continue

                data = list(self.plot_data.get(port, []))
                if not data:
                    continue

                name = self.port_location.get(port, port)
                state_flag = b'f' if self.is_paused_global else b't'

                total = sum(self.weight_a)
                if total > self.weight_total:
                    direction = b'U'
                    self.last_direction = 'U'
                elif total < self.weight_total:
                    direction = b'D'
                    self.last_direction = 'D'
                else:
                    direction = self.last_direction.encode() if isinstance(self.last_direction, str) else b'N'
                self.weight_total = total

                for point in data:
                    try:
                        timestamp_str = point.timestamp.strftime("%H%M%S%f")[:-3]
                        timestamp_int = int(timestamp_str)

                        value1 = float(point.distance)
                        value2 = float(point.intensity)
                        value3 = float(point.temperature)

                        weight_data = struct.pack('<9h', *self.weight_a)
                        name_bytes = name.encode('utf-8')[:16]
                        name_data = name_bytes + b'\x00' * (16 - len(name_bytes))
                        values_data = struct.pack('<fff', value1, value2, value3)

                        binary_data = (
                                struct.pack('<I', timestamp_int)
                                + weight_data + direction + name_data
                                + values_data + state_flag
                        )
                        f.write(binary_data)
                    except Exception as e:
                        print(f"[auto_save 오류] {e}")
                        continue

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

        layout_btn2 = QVBoxLayout()
        layout_btn2.addLayout(weight_input_layout2)
        layout_btn2.addWidget(self.weight_btn_init)
        layout_btn2.addWidget(self.stop_btn)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.sensor_table)
        layout1.addLayout(layout_btn2)

        weight_layout = QHBoxLayout()
        weight_layout.addWidget(self.all_weight_text)
        weight_layout.addWidget(self.all_weight_output)
        weight_layout.addWidget(self.all_weight_unit)

        weight_layout1 = QHBoxLayout()
        weight_layout1.addWidget(self.weight_position)
        weight_layout1.addWidget(self.weight_position_output)

        weight_layout_a = QVBoxLayout()
        weight_layout_a.addLayout(self.weight_table)
        weight_layout_a.addLayout(weight_layout)
        weight_layout_a.addLayout(weight_layout1)

        table_layout = QHBoxLayout()
        table_layout.addLayout(setting_layout)
        table_layout.addLayout(weight_layout_a)

        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graph_change)
        graph_layout.addWidget(self.graph_value)

        layout2 = QVBoxLayout()
        layout2.addLayout(table_layout)
        layout2.addLayout(layout1)

        layout3 = QHBoxLayout()
        layout3.addLayout(layout2)
        layout3.addLayout(graph_layout)

        self.setLayout(layout3)

    # def eventFilter(self, source, event):
    #     if event.type() == QEvent.KeyPress:
    #         key = event.key()
    #
    #         function_keys = {
    #             Qt.Key_P: self.weightP,
    #             Qt.Key_O: self.weightM,
    #             Qt.Key_I: self.weightZ,
    #             Qt.Key_M: self.save,
    #             Qt.Key_K: self.stop,
    #             Qt.Key_L: self.restart
    #         }
    #
    #         if key in function_keys:
    #             function_keys[key]()
    #             return True
    #
    #         key_to_cell = {
    #             Qt.Key_Q: (0, 0), Qt.Key_W: (0, 1), Qt.Key_E: (0, 2),
    #             Qt.Key_A: (1, 0), Qt.Key_S: (1, 1), Qt.Key_D: (1, 2),
    #             Qt.Key_Z: (2, 0), Qt.Key_X: (2, 1), Qt.Key_C: (2, 2)
    #         }
    #
    #         if key in key_to_cell:
    #             row, col = key_to_cell[key]
    #             self.weight_table.setFocus()
    #             self.weight_table.setCurrentCell(row, col)
    #             return True
    #
    #         if key in [Qt.Key_Return, Qt.Key_Enter]:
    #             self.weight_table.clearFocus()
    #             self.setFocus()
    #             return True
    #
    #     return super().eventFilter(source, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Experiment()
    sys.exit(app.exec_())