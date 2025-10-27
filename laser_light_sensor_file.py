import os
import sys

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtWidgets import *
from pyqtgraph import PlotWidget


class LaserLightSensorFile(QWidget):
    def __init__(self, file_name, graphtype='plot'):
        super().__init__()
        self.graph = {}
        self.graphtype = graphtype
        self.file_name = file_name
        self.file_path = os.path.join("log", self.file_name)

        # 데이터 타입 정의
        self.sensor_dtype = None
        self.sensor_data = None
        self.data_by_location = None

        # 그래프 데이터
        self.file_sensor_graph = None
        self.loc_color = {  # 위치당 레이저 그레프 선 색 지정
            'TOP_LEFT'    : 'skyblue',
            'BOTTOM_LEFT' : 'g',
            'TOP_RIGHT'   : 'pink',
            'BOTTOM_RIGHT': 'orange'
        }
        self.graph_grid_coords = {  # 그리드 레이아웃 적용 시 각 센서의 위치
            'TOP_LEFT'    : (0, 0),
            'BOTTOM_LEFT' : (1, 0),
            'TOP_RIGHT'   : (0, 1),
            'BOTTOM_RIGHT': (1, 1)
        }
        self.location_map = {
            0: 'TOP_LEFT',
            1: 'BOTTOM_LEFT',
            2: 'TOP_RIGHT',
            3: 'BOTTOM_RIGHT'
        }
        self.file_sensor_graphs = {}

        self.standard_line_value = 0

        # 초기화 및 데이터 로드
        self.init_data_type()
        self.load_data_from_file()
        self.group_by_location()

        if self.graphtype == 'plot':
            self.init_plot_graph()
        elif self.graphtype == 'scatter':
            self.init_scatter_graph()
        else:
            print("Invalid graphtype")
            sys.exit(1)

    def init_data_type(self):
        self.sensor_dtype = np.dtype([
            ('timestamp', '<u4'),
            ('weights', '<i2', 9),
            ('direction', 'S1'),
            ('name', 'S16'),
            ('location', '<B'),
            ('laser_data', [('distance', '<f4'), ('intensity', '<f4'), ('temperature', '<f4')]),
            ('light_data', [('lux', '<f4'), ('ch0', '<u2'), ('ch1', '<u2')]),
            ('state_flag', 'S1')
        ])

    def load_data_from_file(self):
        np_data = np.fromfile(self.file_path, dtype=self.sensor_dtype)

        # 필요한 필드만 추출해서 DataFrame 생성
        self.sensor_data = pd.DataFrame({
            'timestamp': np_data['timestamp'],
            'location': np_data['location'],
            'distance': np_data['laser_data']['distance'],
            'lux': np_data['light_data']['lux'],
            'ch1': np_data['light_data']['ch1']
        })

    def group_by_location(self):
        # Pandas groupby 사용
        self.data_by_location = dict(tuple(self.sensor_data.groupby('location')))

    def init_plot_graph(self):
        # 기준값 레이아웃
        standard_layout = QHBoxLayout()
        self.standard_label = QLabel('Standard Value : ')
        self.standard_value = QLineEdit()
        self.standard_value.returnPressed.connect(self.save_standard_value)
        standard_layout.addWidget(self.standard_label)
        standard_layout.addWidget(self.standard_value)

        # 그래프 레이아웃
        graph_layout = QGridLayout()
        for location in self.data_by_location:
            loc_name = self.location_map[location]
            data = self.data_by_location[location].reset_index(drop=True)
            self.graph[location] = FileSensorGraphWidget(data, location, self.loc_color[loc_name], self.standard_line_value)
            graph_layout.addWidget(self.graph[location], *self.graph_grid_coords[loc_name])
            self.file_sensor_graphs[loc_name] = self.graph[location]

        # 전체 레이아웃 설정
        layout = QVBoxLayout()
        layout.addLayout(graph_layout)
        layout.addLayout(standard_layout)
        self.setLayout(layout)

    def init_scatter_graph(self):
        # 기준값 레이아웃
        standard_layout = QHBoxLayout()
        self.standard_label = QLabel('Standard Value : ')
        self.standard_value = QLineEdit()
        self.standard_value.returnPressed.connect(self.save_standard_value)
        standard_layout.addWidget(self.standard_label)
        standard_layout.addWidget(self.standard_value)

        # 그래프 레이아웃
        graph_layout = QGridLayout()
        for location in self.data_by_location:
            loc_name = self.location_map[location]
            data = self.data_by_location[location].reset_index(drop=True)
            self.graph[location] = ScatterPlotWidget(data, location, self.standard_line_value)
            graph_layout.addWidget(self.graph[location], *self.graph_grid_coords[loc_name])
            self.file_sensor_graphs[loc_name] = self.graph[location]

        # 전체 레이아웃 설정
        layout = QVBoxLayout()
        layout.addLayout(graph_layout)
        layout.addLayout(standard_layout)
        self.setLayout(layout)

    def save_standard_value(self):
        text = self.standard_value.text().strip()
        self.standard_line_value = int(text)

        # 기준선의 y값을 새로 설정하여 업데이트
        for location in self.data_by_location:
            self.graph[location].standard_line.setValue(self.standard_line_value)
            self.graph[location].standard_line_value = self.standard_line_value
            self.graph[location].update_graph()

        self.standard_value.clear()


class FileSensorGraphWidget(QWidget):
    def __init__(self, data, location, color, standard_line_value):
        super().__init__()
        # 그래프 그리기 데이터
        self.data = data
        self.location = location
        self.color = color
        self.plot_widget = None
        self.plot = None
        self.axis_directions = ['left', 'bottom', 'right', 'top']
        self.laser_plot_curve = None
        self.light_plot_curve = None
        self.ir_plot_curve = None

        # 기준선 및 오차 계산용 데이터
        self.standard_line = None
        self.standard_line_value = standard_line_value
        self.standard_line_label = None
        self.experimental_distance = self.data['distance'].to_numpy() # 측정값은 미리 저장
        self.actual_distance = self.standard_line_value # 기준값

        # 오차값 변수 및 UI 라벨
        self.mae_value = 0
        self.rmse_value = 0
        self.mae_label = None
        self.rmse_label = None
        self.current_range = None  # 범위 초기화

        self.init_graph()

    def init_graph(self):
        # --- UI 요소 생성 ---
        self.text_layout = QHBoxLayout()
        self.standard_value_label = QLabel()
        self.mae_label = QLabel()
        self.rmse_label = QLabel()
        self.text_layout.addWidget(self.standard_value_label)
        self.text_layout.addWidget(self.mae_label)
        self.text_layout.addWidget(self.rmse_label)

        self.plot_widget = PlotWidget()
        self.plot = self.plot_widget.getPlotItem()

        # 그래프 제목 및 축 레이블 설정
        self.plot.setTitle(f'{self.location} Sensor')
        self.plot.setLabel('bottom', 'Time')
        self.plot.setLabel('left', 'Laser Distance')
        self.plot.showAxis('right')
        self.plot.setLabel('right', 'Light (lux)')

        # 전체 레이아웃 구성
        layout = QVBoxLayout()
        layout.addLayout(self.text_layout)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # 그래프 축 라벨 색상을 모두 흰색으로 설정
        for axis in self.axis_directions:
            self.plot.getAxis(axis).setPen(pg.mkPen('w'))

        x = list(range(len(self.data['timestamp'])))
        y_laser = self.experimental_distance # 미리 저장해둔 측정값 사용
        y_light = self.data['lux'].to_numpy()
        y_ir = self.data['ch1'].to_numpy()

        self.laser_plot_curve = self.plot.plot(x, y_laser, pen=pg.mkPen(color=self.color, width=2))
        self.light_plot_curve = self.plot.plot(x, y_light, pen=pg.mkPen(color='w', width=2))
        self.ir_plot_curve = self.plot.plot(x, y_ir, pen=pg.mkPen(color='r', width=2))

        self.legend = self.plot.addLegend(offset=(30, 30))
        self.legend.addItem(self.laser_plot_curve, "Laser")
        self.legend.addItem(self.light_plot_curve, "Light")
        self.legend.addItem(self.ir_plot_curve, "IR")

        # 값 표시용 라벨
        self.value_text = pg.TextItem(text="", anchor=(0, 0))
        self.value_text.setZValue(100)  # 다른 요소들 위에 표시
        self.plot_widget.addItem(self.value_text)

        # 십자선 추가
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        # 마우스 이벤트 연결
        self.plot_widget.scene().sigMouseMoved.connect(self.onMouseMoved)

        # ViewBox에 대한 직접 참조 가져오기
        self.viewbox = self.plot_widget.plotItem.getViewBox()

        # 자동 범위 조정 비활성화 (X, Y 모두)
        self.viewbox.disableAutoRange()

        self.update_graph()

    def calculate_and_update_errors(self):
        """오차를 계산하고 UI 라벨의 텍스트를 업데이트하는 함수"""
        self.mae_value = np.mean(np.abs(self.actual_distance - self.experimental_distance))
        self.rmse_value = np.sqrt(np.mean((self.actual_distance - self.experimental_distance) ** 2))

        self.standard_value_label.setText(f'Standard Value: {self.actual_distance}')
        self.mae_label.setText(f'MAE: {self.mae_value:.2f}')
        self.rmse_label.setText(f'RMSE: {self.rmse_value:.2f}')

    def update_graph(self):
        """기준선이 변경될 때 호출되는 함수"""
        self.actual_distance = self.standard_line_value

        self.calculate_and_update_errors()

        if self.standard_line:
            self.plot.removeItem(self.standard_line)
        self.standard_line = self.plot.addLine(y=self.standard_line_value, pen=pg.mkPen('y', width=2))

    def onMouseMoved(self, pos):
        """마우스 이동 이벤트 핸들러"""
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        # 마우스 좌표를 데이터 좌표로 변환
        mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x = int(mousePoint.x())
        y = mousePoint.y()

        # 십자선 위치 업데이트
        self.vLine.setPos(x)
        self.hLine.setPos(y)

        # 데이터 값 표시
        if self.data is not None and 0 <= x < len(self.data):
            row = self.data.iloc[x]

            # 표시할 항목들을 원하는 순서대로 추가
            text = (
                f"Distance: {row['distance']:.2f}\n"
                f"Light (lux): {row['lux']:.2f}\n"
                f"IR (ch1): {row['ch1']}\n"
            )

            self.value_text.setText(text)

            # 위치 업데이트
            view_range = self.plot_widget.viewRange()
            text_x = max(view_range[0][0], min(x, view_range[0][1] - 100))
            text_y = view_range[1][0] + (view_range[1][1] - view_range[1][0]) * 0.6

            self.value_text.setPos(text_x, y)
            self.value_text.setVisible(True)
        else:
            self.value_text.setVisible(False)


class ScatterPlotWidget(QWidget):
    def __init__(self, data, location, standard_line_value):
        super().__init__()
        self.data = data
        self.location: str = location
        self.standard_line_value = standard_line_value

        # 기준선 및 오차 계산용 데이터
        self.standard_line = None
        self.standard_line_value = standard_line_value

        self.init_graph()
        self.update_graph()

    def init_graph(self):
        x = self.data['distance'].to_numpy()
        y_ir = self.data['ch1'].to_numpy()
        y_lux = self.data['lux'].to_numpy()

        # 그래프 위젯 생성
        self.scatter_widget = pg.PlotWidget()
        self.scatter_widget.setBackground('k')
        self.scatter_widget.setLabel('left', 'lux / IR')
        self.scatter_widget.setLabel('bottom', 'Distance')
        self.scatter_widget.setTitle(f'산점도 (Sensor {self.location})')

        # 자외선 산점도 추가
        self.scatter_ir = pg.ScatterPlotItem(
            x=x,
            y=y_ir,
            pen=None,
            brush='r',
            size=7
        )

        # lux 산점도 추가
        self.scatter_lux = pg.ScatterPlotItem(
            x=x,
            y=y_lux,
            pen=None,
            brush='w',
            size=7
        )

        # 범례(legend) 추가
        self.legend = self.scatter_widget.plotItem.addLegend(offset=(30, 30))
        self.legend.addItem(self.scatter_ir, "IR")
        self.legend.addItem(self.scatter_lux, "lux")

        # 산점도 위젯에 그래프 추가
        self.scatter_widget.addItem(self.scatter_ir)
        self.scatter_widget.addItem(self.scatter_lux)

        # 값 표시용 라벨
        self.value_text = pg.TextItem(text="", anchor=(0, 0))
        self.value_text.setZValue(100)  # 다른 요소들 위에 표시
        self.scatter_widget.addItem(self.value_text)
        
        # 십자선 추가
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.scatter_widget.addItem(self.vLine, ignoreBounds=True)
        self.scatter_widget.addItem(self.hLine, ignoreBounds=True)

        # 마우스 이벤트 연결
        self.scatter_widget.scene().sigMouseMoved.connect(self.onMouseMoved)

        # ViewBox에 대한 직접 참조 가져오기
        self.viewbox = self.scatter_widget.plotItem.getViewBox()

        # 자동 범위 조정 비활성화 (X, Y 모두)
        self.viewbox.disableAutoRange()

        layout = QVBoxLayout()
        layout.addWidget(self.scatter_widget)
        self.setLayout(layout)

    def update_graph(self):
        """기준선이 변경될 때 호출되는 함수"""
        if self.standard_line:
            self.scatter_widget.removeItem(self.standard_line)
        self.standard_line = self.scatter_widget.addLine(x=self.standard_line_value, pen=pg.mkPen('y', width=1))

    def onMouseMoved(self, pos):
        """마우스 이동 이벤트 핸들러 (2차원 산점도용: distance vs lux/ch1)"""
        if not self.scatter_widget.sceneBoundingRect().contains(pos):
            return

        # 마우스 좌표를 데이터 좌표로 변환
        mousePoint = self.scatter_widget.plotItem.vb.mapSceneToView(pos)
        x = mousePoint.x()
        y = mousePoint.y()

        # 십자선 위치 업데이트
        self.vLine.setPos(x)
        self.hLine.setPos(y)

        # 데이터가 있을 때
        if self.data is not None and len(self.data) > 0:
            distances = self.data['distance'].to_numpy()
            lux_values = self.data['lux'].to_numpy()
            ir_values = self.data['ch1'].to_numpy()

            # 마우스 위치에 가장 가까운 점 찾기 (lux, IR 모두 비교)
            # 우선 lux 기준
            distances_2d = np.sqrt((distances - x) ** 2 + (lux_values - y) ** 2)
            idx_lux = np.argmin(distances_2d)
            d_lux = distances_2d[idx_lux]

            # 그리고 IR 기준
            distances_2d_ir = np.sqrt((distances - x) ** 2 + (ir_values - y) ** 2)
            idx_ir = np.argmin(distances_2d_ir)
            d_ir = distances_2d_ir[idx_ir]

            # lux, IR 중 더 가까운 점 선택
            if d_lux < d_ir:
                idx = idx_lux
                y_type = 'lux'
            else:
                idx = idx_ir
                y_type = 'ch1'

            row = self.data.iloc[idx]

            # 표시할 텍스트 구성
            text = (
                f'Distance: {row["distance"]:.2f}\n'
                f'Light (lux): {row["lux"]:.2f}\n'
                f'IR (ch1): {row["ch1"]}\n'
                f'(Nearest: {y_type})'
            )

            self.value_text.setText(text)

            # 텍스트 표시 위치 업데이트
            view_range = self.scatter_widget.viewRange()
            text_x = max(view_range[0][0], min(x, view_range[0][1] - 50))
            text_y = y

            self.value_text.setPos(text_x, text_y)
            self.value_text.setVisible(True)
        else:
            self.value_text.setVisible(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLightSensorFile()
    sys.exit(app.exec_())