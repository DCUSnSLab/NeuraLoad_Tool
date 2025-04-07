import datetime
import os
import sys
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from GUIController import GUIController


class Experiment(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager
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
        self.is_paused_global = True
        self.aaaa = False
        self.save_graph_max = 500
        self.save_graph_min = 0

        self.port_comboboxes = {}
        self.port_column_index = {}
        self.port_location = {}
        self.port_colors = {
            'BottomLeft': 'r',
            'TopRight': 'g',
            'TopLeft': 'b',
            'BottomRight': 'orange',
            'IMU': 'yellow',
            'etc': 'purple'
        }
        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}

        self.ports = self.serial_manager.ports

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

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(self.weightP)

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(self.weightM)

        self.weight_btn_z = QPushButton('리셋', self)
        self.weight_btn_z.clicked.connect(self.weightZ)

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
        self.GUIThread = GUIController(self, self.serial_manager.threads)
        self.GUIThread.plot_updated.connect(self.updateGraph)
        self.GUIThread.start()

    def updateGraph(self, port=None):
        try:
            # 그래프 Y축 범위 설정
            self.graph_change.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)
            self.graph_value.getPlotItem().setYRange(min=self.save_graph_min, max=self.save_graph_max)

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
                        location_name = self.port_comboboxes[port].currentText().strip() if port in self.port_comboboxes else ''
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
                    if isinstance(point, (list, tuple)) and len(point) > 1:
                        try:
                            # value 부분이 숫자인지 확인
                            y_value = float(point[1])
                            y_values.append(y_value)
                        except (ValueError, TypeError):
                            # 숫자로 변환할 수 없는 경우 임의 값 사용
                            y_values.append(0)
                    else:
                        y_values.append(0)
                
                # 변화량 데이터 계산
                change_values = []
                if len(self.plot_change[port]) > 0:
                    # 기준값을 첫번째 유효한 값으로 설정
                    base_val = None
                    for point in self.plot_change[port]:
                        if isinstance(point, (list, tuple)) and len(point) > 1:
                            try:
                                base_val = float(point[1])
                                break
                            except (ValueError, TypeError):
                                pass
                    
                    # 기준값이 없으면 0으로 설정
                    if base_val is None:
                        base_val = 0
                    
                    # 변화량 계산
                    for point in self.plot_change[port]:
                        if isinstance(point, (list, tuple)) and len(point) > 1:
                            try:
                                value = float(point[1])
                                change_values.append(value - base_val)
                            except (ValueError, TypeError):
                                change_values.append(0)
                        else:
                            change_values.append(0)
                
                # 데이터가 준비되면 그래프 업데이트
                if len(y_values) > 0 and len(x) == len(y_values):
                    self.plot_curve[port].setData(x, y_values)
                
                if len(change_values) > 0 and len(x) == len(change_values):
                    self.plot_curve_change[port].setData(x, change_values)
                
                # 실험 중일 때만 데이터 처리 및 테이블 업데이트
                if self.aaaa and port in self.port_index:
                    # 최신 값 표시
                    value = -1
                    if len(y_values) > 0:
                        value = y_values[-1]
                    
                    # 테이블 업데이트
                    location = self.port_index[port]
                    self.sensor_table.setItem(0, location, QTableWidgetItem(str(value)))
                    
                    # 데이터 저장 처리
                    self.handle_serial_data(port, self.plot_data[port])
        except Exception as e:
            print(f"그래프 업데이트 중 오류 발생: {e}")
            import traceback
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
            direction_byte = b'U';  self.last_direction = 'U'
        elif total < self.weight_total:
            direction_byte = b'D';  self.last_direction = 'D'
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
            last_point = data[-1]
            if not isinstance(last_point, (list, tuple)) or len(last_point) < 4:
                print(f"[경고] 잘못된 포맷: {last_point}")
                return

            timestamp_str = last_point[0]
            try:
                timestamp_int = int(timestamp_str.replace('_', ''))
            except ValueError:
                print(f"[경고] 타임스탬프 변환 실패: {timestamp_str}")
                return

            try:
                value1 = float(last_point[1])
                value2 = float(last_point[2])
                value3 = float(last_point[3])
            except (ValueError, IndexError):
                print(f"[경고] 값 변환 실패: {last_point}")
                return
                
            # 패킹 및 처리 코드
            weight_bin = struct.pack('<9h', *self.weight_a)
            name_bytes = name.encode('utf-8')[:16]
            name_bin = name_bytes + b'\x00' * (16 - len(name_bytes))
            values_bin = struct.pack('<fff', value1, value2, value3)
            record = struct.pack('<I', timestamp_int) + weight_bin + direction_byte + name_bin + values_bin + state_flag

            # 파일에 append
            with open(file_path, 'ab') as f:
                f.write(record)
        except Exception as e:
            print(f"[오류] 데이터 처리 중 예외 발생: {e}")



    def save_serial_data(self, port, data):
        if port not in self.port_index:
            return
            
        # 데이터가 비어있는지 확인
        if not data:
            # 디버그 수준을 낮추기 위해 경고 출력 생략
            # print(f"[정보] {port}에 대한 저장할 데이터가 아직 없습니다.")
            return

        os.makedirs("log", exist_ok=True)
        filename = datetime.datetime.now().strftime("raw_data_%Y-%m-%d.txt")
        self.raw_data_file = open(os.path.join("log", filename), "a", encoding="utf-8")

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
        state_flag = 'f' if self.is_paused_global else 't'
        name = self.port_location.get(port, port)

        # 데이터 포맷 정리
        if isinstance(data, deque):
            data = list(data)
        if not isinstance(data, list) or len(data) < 1:
            print(f"[경고] 예상치 못한 데이터 형식 또는 길이 부족: {data}")
            return

        try:
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
        except Exception as e:
            print(f"[오류] 데이터 저장 중 예외 발생: {e}")



    def stop(self):
        self.aaaa = True  # 전역 상태 갱신

        QCoreApplication.processEvents()

    def restart(self):
        self.aaaa = False  # 전역 상태 갱신

    def toggle_btn(self):
        if self.stop_btn.isChecked():
            self.aaaa = True
            self.is_paused_global = False
            QCoreApplication.processEvents()
            self.stop_btn.setText("실험 종료")
        else:
            self.aaaa = False
            self.is_paused_global = True
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
            print(f"onCellChanged 오류: {e}")
            # 로그 출력 객체가 있는지 확인
            if hasattr(self, 'log_output'):
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
        os.makedirs("log", exist_ok=True)
        filename = datetime.datetime.now().strftime("raw_data_%Y-%m-%d.bin")
        file_path = os.path.join("log", filename)
        with open(file_path, "ab") as f:  # 바이너리 append
            for port in self.ports:
                if port not in self.port_index:
                    continue

                data = self.plot_data.get(port, [])
                if not data:
                    continue

                name = self.port_location.get(port, port)
                state_flag = b'f' if self.is_paused_global else b't'

                # 무게 변화 방향 계산
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
                    if not isinstance(point, (list, tuple)) or len(point) < 4:
                        continue

                    timestamp = point[0]
                    try:
                        value1 = float(point[1])
                        value2 = float(point[2])
                        value3 = float(point[3])
                    except (ValueError, IndexError):
                        continue

                    # 타임스탬프 변경 ex)15_17_48_666 → 151748666
                    try:
                        timestamp_int = int(timestamp.replace('_', ''))
                    except:
                        continue

                    # 무게: 9개 int16
                    weight_data = struct.pack('<9h', *self.weight_a)

                    # 포트 이름: 16바이트 문자열 (패딩 포함)
                    name_bytes = name.encode('utf-8')[:16]
                    name_data = name_bytes + b'\x00' * (16 - len(name_bytes))

                    # 센서값 3개: float32
                    values_data = struct.pack('<fff', value1, value2, value3)

                    # 최종 패킹
                    binary_data = struct.pack('<I', timestamp_int) + weight_data + direction + name_data + values_data + state_flag
                    f.write(binary_data)

    def btn_save(self):
        try:
            timestamp = datetime.datetime.now().strftime("save_%H_%M_%S_%f")[:-3]
            folder_name = datetime.datetime.now().strftime("saved_data_%Y-%m-%d")
            self.save(timestamp, folder_name)
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"오류 발생: {e}", QMessageBox.Ok)

    def save(self, timestamp, folder_name):
        print("일반 save ㅇㅇ")
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
        layout_btn2.addWidget(self.weight_btn_z)
        layout_btn2.addWidget(self.stop_btn)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.sensor_table)
        layout1.addLayout(layout_btn2)

        table_layout = QHBoxLayout()
        table_layout.addLayout(setting_layout)
        table_layout.addWidget(self.weight_table)

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
        if hasattr(self, "sensor_data_file") and not self.sensor_data_file.closed:
            self.sensor_data_file.close()

        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Experiment()
   sys.exit(app.exec_())