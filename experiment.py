import datetime
import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from arduino_manager import SerialThread, get_arduino_ports

class Experiment(QWidget):
    def __init__(self):
        super().__init__()
        self.threads = []
        self.port_index = {}
        self.weight_a = [0] * 9
        self.count = 0
        self.weight_total = 0
        self.last_direction = '-'
        self.ports = get_arduino_ports()

        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}

        self.setting()
        self.setupUI()
        self.setup()
        self.startSerialThread()
        self.installEventFilter(self)

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(600000)

    def setting(self):
        self.port_location = {}
        self.port_colors = {}
        for i, port in enumerate(self.ports):
            if i == 0:
                name = 'TopLeft'
                color = 'r'
            elif i == 1:
                name = 'BottomLeft'
                color = 'g'
            elif i == 2:
                name = 'LeftRight'
                color = 'b'
            elif i == 3:
                name = 'RightLeft'
                color = 'orange'
            elif i == 4:
                name = 'IMU'
                color = 'yellow'
            else:
                name = ''
                color = 'purple'

            self.port_location[port] = name
            self.port_colors[name] = color

    def setupUI(self):
        self.sensor_table = QTableWidget()
        self.sensor_table.setColumnCount(len(self.ports))
        self.sensor_table.setRowCount(1)
        for i in range(len(self.ports)):
            port = self.ports[i]
            name = self.port_location.get(port, "")
            self.sensor_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
        self.sensor_table.setVerticalHeaderLabels(['value'])
        self.sensor_table.setMaximumHeight(200)
        self.sensor_table.setMinimumHeight(150)
        self.sensor_table.setMaximumWidth(500)
        self.sensor_table.setMinimumWidth(700)

        self.logging = QTableWidget()
        self.logging.setColumnCount(5)
        self.logging.setHorizontalHeaderLabels(['시간', '무게', '무게 변화', '위치', '로그'])
        self.logging.setMinimumHeight(300)
        self.logging.setMinimumWidth(300)
        self.logging.horizontalHeader().setStretchLastSection(True)

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
        self.save_btn.clicked.connect(self.btn_save)

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("Laser Change")
        self.graph_change.setLabel("left", "Change")
        self.graph_change.setLabel("bottom", "Time")
        self.graph_change.addLegend(offset=(30, 30))
        self.graph_change.setMinimumWidth(500)

        self.graph_value = pg.PlotWidget()
        self.graph_value.setTitle("Sensor")
        self.graph_value.setLabel("left", "Value")
        self.graph_value.setLabel("bottom", "Time")
        self.graph_value.setMinimumWidth(500)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #F2F2F2;")
        self.log_output.append(str(self.port_location))

    def startSerialThread(self):
        for i, port in enumerate(self.ports):
            thread = SerialThread(port)
            thread.data_received.connect(self.handle_serial_data)
            thread.start()
            self.threads.append(thread)
            self.port_index[port] = i

        for port in self.ports:
            self.plot_data[port] = deque(maxlen=300)
            self.plot_change[port] = deque(maxlen=300)
            color = self.port_colors.get(self.port_location[port])

            self.plot_curve[port] = self.graph_value.plot(
                pen=pg.mkPen(color=color, width=1),
                name=self.port_location.get(port, port)
            )

            self.plot_curve_change[port] = self.graph_change.plot(
                pen=pg.mkPen(color=color, width=1),
                name=self.port_location.get(port, port)
            )

    def handle_serial_data(self, port, data):
        if port in self.port_index:
            try:
                value = int(data.strip())
            except ValueError:
                return

            self.plot_data[port].append(value)
            self.plot_change[port].append(value)

            x = list(range(len(self.plot_data[port])))
            y = list(self.plot_data[port])

            base_val = self.plot_change[port][0] if len(self.plot_change[port]) > 0 else 0
            change = [v - base_val for v in self.plot_change[port]]

            time = datetime.datetime.now().strftime("%M_%S_%f")[:-3]

            self.log_output.append(time + " " + str(self.port_location[port]) + ": " + str(change[-1]))

            self.plot_curve[port].setData(x, y)
            self.plot_curve_change[port].setData(x,change)

            location = self.port_index[port]
            self.sensor_table.setItem(0, location, QTableWidgetItem(data))

            current_row = self.logging.rowCount()
            self.logging.insertRow(current_row)
            self.logging.setItem(current_row, 0, QTableWidgetItem(time))
            self.logging.setItem(current_row, 1, QTableWidgetItem(str(self.weight_a)))

            total =sum(self.weight_a)
            if total > self.weight_total:
                direction = 'U'
                self.last_direction = direction
            elif total < self.weight_total:
                direction = 'D'
                self.last_direction = direction
            else:
                direction = self.last_direction

            self.weight_total = total

            self.logging.setItem(current_row, 2, QTableWidgetItem(direction))

            name = self.port_location.get(port, "")
            self.logging.setItem(current_row, 3, QTableWidgetItem(name))

            self.logging.setItem(current_row, 4, QTableWidgetItem(data))
            self.logging.scrollToBottom()

    def stop(self):
        for thread in self.threads:
            thread.pause()
        QCoreApplication.processEvents()

    def restart(self):
        for thread in self.threads:
            thread.resume()

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
            headers = ['Logged Time', '무게', '무게 변화량', '포트', '로그']
            file.write("\t".join(headers) + "\n")

            for row in range(self.logging.rowCount()):
                current_time = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]

                weight = self.logging.item(row, 0).text() if self.logging.item(row, 0) else ""

                weight_change = self.logging.item(row, 1).text() if self.logging.item(row, 1) else ""

                port = self.logging.item(row, 2).text() if self.logging.item(row, 2) else ""

                log_data = self.logging.item(row, 3).text() if self.logging.item(row, 3) else ""
                log_content = ",".join(log_data.split(','))

                file.write(f"{current_time}\t{weight}\t{weight_change}\t{port}\t{log_content}\n")

        row_position = self.save_file_box_log.rowCount()
        self.save_file_box_log.insertRow(row_position)
        self.save_file_box_log.setItem(row_position, 0, QTableWidgetItem(file_name))
        self.save_file_box_log.scrollToBottom()

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
        table_layout.addWidget(self.sensor_table)
        table_layout.addWidget(self.weight_table)

        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graph_change)
        graph_layout.addWidget(self.graph_value)
        graph_layout.addWidget(self.log_output)

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
        event.accept()

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Experiment()
   sys.exit(app.exec_())