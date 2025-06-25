from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from datainfo import SENSORLOCATION
import datetime

class LightSensorTab(QWidget):
    def __init__(self, serial_manager=None):
        super().__init__()
        self.serial_manager = serial_manager
        self.sensor_data_labels = {}
        self.initUI()
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_sensor_data)
        self.update_timer.start(100)
    
    def initUI(self):
        self.setWindowTitle("Light Sensor Data")
        
        main_layout = QVBoxLayout()
        
        sensors_layout = QHBoxLayout()
        
        if self.serial_manager and hasattr(self.serial_manager, 'sensors'):
            for sensor in self.serial_manager.sensors:
                location = sensor.sensorLoc
                location_names = {
                    SENSORLOCATION.TOP_LEFT: "좌상단",
                    SENSORLOCATION.BOTTOM_LEFT: "좌하단",
                    SENSORLOCATION.TOP_RIGHT: "우상단", 
                    SENSORLOCATION.BOTTOM_RIGHT: "우하단"
                }
                
                name = location_names.get(location, f"센서_{sensor.port}")
                group_box = self.create_sensor_group(location, name, sensor.port)
                sensors_layout.addWidget(group_box)
        else:
            no_sensor_label = QLabel("No sensor connected")
            no_sensor_label.setAlignment(Qt.AlignCenter)
            no_sensor_label.setStyleSheet("color: red; font-size: 14px;")
            sensors_layout.addWidget(no_sensor_label)
        
        main_layout.addLayout(sensors_layout)
        
        #self.create_summary_table()
        #main_layout.addWidget(self.summary_table)
        
        self.setLayout(main_layout)
    
    def create_sensor_group(self, location, name, port=None):
        port_info = f" ({port})" if port else ""
        group_box = QGroupBox(f"{name} sensor{port_info}")
        group_box.setFont(QFont("Arial", 10, QFont.Bold))
        
        layout = QGridLayout()
        
        light_data_fields = [
            ("lux", "lux", "lx"),
            ("gainMultiplier", "gainMultiplier", "x"),
            ("integrationTime", "integrationTime", "ms"),
            ("CPL", "cpl", ""),
            ("visible", "visible", ""),
            ("ch 0", "ch0", ""),
            ("ch 1", "ch1", ""),
            ("fullLuminosity", "fullLuminosity", "")
        ]
        
        self.sensor_data_labels[location] = {}
        
        for i, (label_text, field_name, unit) in enumerate(light_data_fields):
            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Arial", 9))
            layout.addWidget(label, i, 0)
            
            value_label = QLabel("-- " + unit)
            value_label.setFont(QFont("Arial", 9, QFont.Bold))
            value_label.setStyleSheet("color: blue; background-color: #f0f0f0; padding: 2px;")
            layout.addWidget(value_label, i, 1)
            
            self.sensor_data_labels[location][field_name] = (value_label, unit)
        
        time_label = QLabel("Last update:")
        layout.addWidget(time_label, len(light_data_fields), 0)
        
        time_value = QLabel("--")
        time_value.setFont(QFont("Arial", 8))
        time_value.setStyleSheet("color: gray;")
        layout.addWidget(time_value, len(light_data_fields), 1)
        
        self.sensor_data_labels[location]['timestamp'] = (time_value, "")
        
        group_box.setLayout(layout)
        return group_box
    
    def create_summary_table(self):
        self.summary_table = QTableWidget()
        
        sensor_count = 0
        row_headers = []
        if self.serial_manager and hasattr(self.serial_manager, 'sensors'):
            sensor_count = len(self.serial_manager.sensors)
            location_names = {
                SENSORLOCATION.TOP_LEFT: "좌상단",
                SENSORLOCATION.BOTTOM_LEFT: "좌하단",
                SENSORLOCATION.TOP_RIGHT: "우상단", 
                SENSORLOCATION.BOTTOM_RIGHT: "우하단"
            }
            
            for sensor in self.serial_manager.sensors:
                name = location_names.get(sensor.sensorLoc, f"센서_{sensor.port}")
                row_headers.append(f"{name} ({sensor.port})")
        else:
            sensor_count = 1
            row_headers = ["No sensor connected"]
        
        self.summary_table.setRowCount(sensor_count)
        self.summary_table.setColumnCount(9)  # 8개 조도 데이터 + 센서 위치
        
        headers = ["sensor location", "lux", "gainMultiplier", "integrationTime", "CPL", "visible", "ch 0", "ch 1", "fullLuminosity"]
        self.summary_table.setHorizontalHeaderLabels(headers)
        
        self.summary_table.setVerticalHeaderLabels(row_headers)
        self.summary_table.resizeColumnsToContents()
        self.summary_table.setAlternatingRowColors(True)
        
        # 초기 데이터로 채우기
        for row in range(sensor_count):
            for col in range(9):
                if col == 0:
                    item = QTableWidgetItem(row_headers[row] if row < len(row_headers) else "--")
                else:
                    item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignCenter)
                self.summary_table.setItem(row, col, item)
    
    def update_sensor_data(self):
        if not self.serial_manager or not hasattr(self.serial_manager, 'candidate_window'):
            return
        
        if not self.serial_manager.candidate_window:
            return
        
        try:
            sensors_data = self.serial_manager.candidate_window
            
            for sensor_data in sensors_data:
                location = sensor_data.location
                
                if location in self.sensor_data_labels:
                    labels_dict = self.sensor_data_labels[location]
                    
                    data_updates = {
                        'lux': f"{sensor_data.lux:.2f}",
                        'gainMultiplier': f"{sensor_data.gainMultiplier:.2f}",
                        'integrationTime': f"{sensor_data.integrationTime:.2f}",
                        'cpl': f"{sensor_data.cpl:.2f}",
                        'visible': f"{sensor_data.visible}",
                        'ch0': f"{sensor_data.ch0}",
                        'ch1': f"{sensor_data.ch1}",
                        'fullLuminosity': f"{sensor_data.fullLuminosity}"
                    }
                    
                    for field, value in data_updates.items():
                        if field in labels_dict:
                            label, unit = labels_dict[field]
                            label.setText(f"{value} {unit}")
                    
                    if 'timestamp' in labels_dict:
                        time_label, _ = labels_dict['timestamp']
                        time_str = sensor_data.timestamp.strftime("%H:%M:%S")
                        time_label.setText(time_str)
                    
                    # 요약 테이블 업데이트 - 실제 연결된 센서에서의 인덱스 찾기
                    if self.serial_manager and hasattr(self.serial_manager, 'sensors'):
                        for row, sensor in enumerate(self.serial_manager.sensors):
                            if sensor.sensorLoc == location:
                                location_names = {
                                    SENSORLOCATION.TOP_LEFT: "좌상단",
                                    SENSORLOCATION.BOTTOM_LEFT: "좌하단",
                                    SENSORLOCATION.TOP_RIGHT: "우상단", 
                                    SENSORLOCATION.BOTTOM_RIGHT: "우하단"
                                }
                                
                                location_name = location_names.get(location, f"센서_{sensor.port}")
                                table_data = [
                                    f"{location_name} ({sensor.port})",
                                    f"{sensor_data.lux:.1f}",
                                    f"{sensor_data.gainMultiplier:.1f}",
                                    f"{sensor_data.integrationTime:.1f}",
                                    f"{sensor_data.cpl:.2f}",
                                    str(sensor_data.visible),
                                    str(sensor_data.ch0),
                                    str(sensor_data.ch1),
                                    str(sensor_data.fullLuminosity)
                                ]
                                
                                for col, data in enumerate(table_data):
                                    item = QTableWidgetItem(data)
                                    item.setTextAlignment(Qt.AlignCenter)
                                    self.summary_table.setItem(row, col, item)
                                break
        
        except Exception as e:
            pass
            #print(f"[LightSensorTab] data update error: {e}")
    
    def set_serial_manager(self, serial_manager):
        self.serial_manager = serial_manager