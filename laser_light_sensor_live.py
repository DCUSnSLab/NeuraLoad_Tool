import sys
import traceback
from collections import deque

import pyqtgraph as pg
from PyQt5.QtWidgets import *
from pyqtgraph import PlotWidget, ViewBox, TextItem
from pyqtgraph.Qt import QtGui

from GUIController import GUIController


class LaserLightSensorLive(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager
        self.sensor_graph = {}
        self.port_color = {
            'TOP_LEFT'    : 'skyblue',
            'BOTTOM_LEFT' : 'g',
            'TOP_RIGHT'   : 'pink',
            'BOTTOM_RIGHT': 'orange'
        }
        self.graph_grid_coords = {
            'TOP_LEFT'    : (0, 0),
            'BOTTOM_LEFT' : (1, 0),
            'TOP_RIGHT'   : (0, 1),
            'BOTTOM_RIGHT': (1, 1)
        }
        self.plot_data = {}
        self.laser_plot_curve = {}
        self.light_plot_curve = {}
        self.ir_plot_curve = {}
        self.standard_line_value = 0

        self.initialize_port_data()
        self.initialize_sensor_graph()
        self.setup_ui()
        self.start_gui_thread()

    def initialize_port_data(self):
        for sensor in self.serial_manager.sensors:
            port = sensor.port
            if port in self.plot_data: continue
            self.plot_data[port] = deque(maxlen=300)
            print(f"포트 초기화 완료: {port} ({sensor.sensorLoc.name})")

    def initialize_sensor_graph(self):
        for sensor in self.serial_manager.sensors:
            port, loc_name, color = sensor.port, sensor.sensorLoc.name, self.port_color[sensor.sensorLoc.name]
            self.sensor_graph[port] = LiveSensorGraph(loc_name, color)
            self.laser_plot_curve[port] = self.sensor_graph[port].laser_line
            self.light_plot_curve[port] = self.sensor_graph[port].light_line
            self.ir_plot_curve[port] = self.sensor_graph[port].ir_line

    def start_gui_thread(self):
        print('start GUIThread')
        self.GUIThread = GUIController(self, self.serial_manager, 'LaserLightSensor')
        self.GUIThread.plot_updated.connect(self.update_graph)
        self.GUIThread.start()

    def setup_ui(self):
        """UI가 매우 단순해집니다."""
        grid_info_layout = QGridLayout()

        # 기준선 레이아웃 설정
        standard_layout = QHBoxLayout()
        self.standard_line_lable = QLabel('Standard Value : ')
        self.standard_value = QLineEdit()
        self.standard_value.returnPressed.connect(self.save_standard_value)
        standard_layout.addWidget(self.standard_line_lable)
        standard_layout.addWidget(self.standard_value)

        for sensor in self.serial_manager.sensors:
            graph_widget = self.sensor_graph[sensor.port]
            grid_info_layout.addWidget(graph_widget, *self.graph_grid_coords[sensor.sensorLoc.name])

        # 전체 레이아웃 설정
        layout = QVBoxLayout()
        layout.addLayout(grid_info_layout)
        layout.addLayout(standard_layout)
        self.setLayout(layout)

    def update_graph(self, port=None):
        try:
            ports_to_update = [port] if port else [sensor.port for sensor in self.serial_manager.sensors]

            for port in ports_to_update:
                if not self.plot_data.get(port):
                    continue

                if self.plot_data[port]:
                    last_point = self.plot_data[port][-1]  # 가장 마지막 데이터
                    try:
                        laser_val = float(last_point.distance)
                        light_val = float(last_point.lux)
                        ir_val = float(last_point.ch1)
                        # LiveSensorGraph 객체의 업데이트 메서드 호출
                        self.sensor_graph[port].update_text_values(self.standard_line_value, laser_val, light_val, ir_val)
                    except (ValueError, AttributeError):
                        # 데이터에 문제가 있을 경우 기본값으로 업데이트
                        self.sensor_graph[port].update_text_values(0, 0, 0, 0)

                # 그래프 선을 그리는 로직은 그대로 유지
                x_value = list(range(len(self.plot_data[port])))
                y_laser_values = [p.distance for p in self.plot_data[port]]
                y_light_values = [p.lux for p in self.plot_data[port]]
                y_ir_values = [p.ch1 for p in self.plot_data[port]]

                if y_laser_values: self.laser_plot_curve[port].setData(x_value, y_laser_values)
                if y_light_values: self.light_plot_curve[port].setData(x_value, y_light_values)
                if y_ir_values: self.ir_plot_curve[port].setData(x_value, y_ir_values)

        except Exception as e:
            print(f"그래프 업데이트 중 오류 발생: {e}")
            traceback.print_exc()

    def save_standard_value(self):
        text = self.standard_value.text().strip()
        if text.isdigit():
            self.standard_line_value = int(text)
            for sensor in self.serial_manager.sensors:
                port = sensor.port
                self.sensor_graph[port].standard_line.setValue(self.standard_line_value)
            self.standard_value.clear()


class LiveSensorGraph(QWidget):
    def __init__(self, sensor_location, color):
        super().__init__()
        self.plot_widget = None
        self.plot = None
        self.sensor_location = sensor_location
        self.color = color
        self.standard_line_value = 0
        self.axis_directions = ['left', 'bottom', 'right', 'top']

        self.standard_value_label = QLabel('Standard Value: 0')
        self.laser_label = QLabel('Laser: 0.00')
        self.light_label = QLabel('Light: 0.00')
        self.ir_label = QLabel('IR: 0.00')

        self.init_graph()

        text_layout = QHBoxLayout()
        text_layout.addWidget(self.standard_value_label)
        text_layout.addWidget(self.laser_label)
        text_layout.addWidget(self.light_label)
        text_layout.addWidget(self.ir_label)

        layout = QVBoxLayout()
        layout.addLayout(text_layout)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def update_text_values(self, standard_val, laser_val, light_val, ir_val):
        """최신 센서 값으로 라벨 텍스트를 업데이트합니다."""
        self.standard_value_label.setText(f'Standard Value: {standard_val}')
        self.laser_label.setText(f'Laser: {laser_val:.2f}')
        self.light_label.setText(f'Light: {light_val:.2f}')
        self.ir_label.setText(f'IR: {ir_val:.2f}')

    def init_graph(self):
        """
        센서 데이터를 시각화하기 위한 그래프 초기화 함수.
        Laser, Light, IR 데이터를 각각의 축과 라인으로 표시.
        """

        # 기본 PlotWidget 생성 및 기본 설정
        self.plot_widget = PlotWidget()
        self.plot = self.plot_widget.getPlotItem()

        # 그래프 제목 및 축 레이블 설정
        self.plot.setTitle(f'{self.sensor_location} Sensor')
        self.plot.setLabel('bottom', 'Time')
        self.plot.setLabel('left', 'Laser Distance')
        self.plot.setLabel('right', 'Light (lux) and IR')  # 오른쪽 축은 조도/IR 데이터용
        self.plot.showAxis('right')

        # 축 색상 흰색
        for axis in self.axis_directions:
            self.plot.getAxis(axis).setPen(pg.mkPen('w'))

        # 왼쪽 축 (Laser) 라인 생성
        self.laser_line = self.plot.plot(
            pen=pg.mkPen(self.color, width=1),
            name="Laser"
        )
        self.plot.vb.setYRange(0, 800)  # Laser 거리 범위 설정

        # 오른쪽 축 (Light, IR) ViewBox 생성 및 설정
        self.right_viewbox = ViewBox()
        self.plot.scene().addItem(self.right_viewbox)

        # 오른쪽 축과 ViewBox 연결
        self.plot.getAxis("right").linkToView(self.right_viewbox)
        self.right_viewbox.setXLink(self.plot)  # X축 동기화
        self.right_viewbox.setRange(yRange=(0, 1000))  # Light/IR 데이터 범위 설정

        # Light, IR 라인 추가
        self.light_line = pg.PlotDataItem(pen=pg.mkPen('w', width=1), name="Light")
        self.ir_line = pg.PlotDataItem(pen=pg.mkPen('r', width=1), name="IR")
        self.right_viewbox.addItem(self.light_line)
        self.right_viewbox.addItem(self.ir_line)

        # 범례(legend) 추가
        self.legend = self.plot.addLegend(offset=(30, 30))
        self.legend.addItem(self.laser_line, "Laser")
        self.legend.addItem(self.light_line, "Light")
        self.legend.addItem(self.ir_line, "IR")

        # 기준선 추가
        self.standard_line = self.plot.addLine(
            y=self.standard_line_value,
            pen=pg.mkPen('y', width=2)
        )

        # 뷰 크기 변경 시 오른쪽 ViewBox 갱신 이벤트 연결
        self.plot.vb.sigResized.connect(self.update_views)

    def update_views(self):
        self.right_viewbox.setGeometry(self.plot.vb.sceneBoundingRect())
        self.right_viewbox.linkedViewChanged(self.plot.vb, self.right_viewbox.XAxis)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLightSensorLive()
    sys.exit(app.exec_())
