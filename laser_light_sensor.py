import sys
from PyQt5.QtWidgets import *
from collections import deque
import pyqtgraph as pg
from pyqtgraph import PlotWidget, ViewBox

from GUIController import GUIController
import traceback

class LaserLightSensor(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager # 센서 시리얼
        self.sensor_graph = {}    # 센서 그래프 위젯 저장
        self.save_graph_max = 750 # 그래프 y축 최대값
        self.save_graph_min = 600 # 그래프 y축 최소값
        self.port_color = {       # 위치당 레이저 그레프 선 색 지정 (실험 데이터 수집 탭과 동일한 색 지정)
            'TOP_LEFT'     : 'b',
            'BOTTOM_LEFT'  : 'g',
            'TOP_RIGHT'    : 'r',
            'BOTTOM_RIGHT' : 'orange'
        }
        self.graph_grid_coords = ((0, 0), (1, 0), (0, 1), (1, 1)) # 그리드 레이아웃 적용 시 각 센서의 위치
        self.laser_plot_data = {}  # 각 레이저 센서의 데이터를 저장
        self.light_plot_data = {}  # 각 조도 센서의 데이터를 저장
        self.laser_plot_curve = {} # 각 레이저 센서의 선 정보를 저장
        self.light_plot_curve = {} # 각 조도 센서의 선 정보를 저장

        # 딕셔너리 초기화
        self.initialize_port_data()    # 포트 데이터 초기화
        self.initialize_sensor_graph() # 포트 정보를 기반으로 그래프 객체 초기화
        self.setup_ui()                # UI 셋업
        self.start_gui_thread()        # GUI 쓰레드 시작

    def initialize_sensor_graph(self):
        for sensor in self.serial_manager.sensors:
            port = sensor.port
            sensor_location = sensor.sensorLoc.name  # 센서 위치 이름 가져오기
            color = self.port_color[sensor_location] # 센서 위치 이름에 따라 색 가져오기

            self.sensor_graph[port] = SensorGraph(sensor_location, color)    # 포트별 그래프 객체 생성
            self.laser_plot_curve[port] = self.sensor_graph[port].laser_line # 각 레이저 센서의 선 정보 가져오기
            self.light_plot_curve[port] = self.sensor_graph[port].light_line # 각 조도 센서의 선 정보 가져오기

    def initialize_port_data(self):
        # SerialManager의 포트 정보를 기반으로 데이터 딕셔너리 초기화
        for sensor in self.serial_manager.sensors:
            port = sensor.port
            sensor_location = sensor.sensorLoc.name # 센서 위치 이름 가져오기

            # 포트가 이미 초기화되어 있으면 건너뜀
            if port in self.laser_plot_data and port in self.light_plot_data:
                continue

            self.laser_plot_data[port] = deque(maxlen=300) # 최대 길이 300 데크로 레이저 센서 데이터 저장
            self.light_plot_data[port] = deque(maxlen=300) # 최대 길이 300 데트로 조도 센서 데이터 저장

            print(f"포트 초기화 완료: {port} ({sensor_location})")

    def start_gui_thread(self):
        print('start GUIThread')
        # 쓰레드에 SerialManager의 쓰레드도 전달
        self.GUIThread = GUIController(self, self.serial_manager, 'LaserLightSensor')
        self.GUIThread.plot_updated.connect(self.update_graph) # 센서 데이터 수신 시 plot_updated 시그널 발생 → 그래프 업데이트 수행
        self.GUIThread.start()

    def setup_ui(self):
        layout = QGridLayout() # 그리드 레이아웃으로 설정

        for sensor in self.serial_manager.sensors:
            index = sensor.sensorLoc.value         # 각 센서 위치의 인덱스를 받아옴
            graph = self.sensor_graph[sensor.port] # 각 센서의 그래프 객체를 받아옴

            layout.addWidget(graph, *self.graph_grid_coords[index]) # 그래프 레이아웃 설정

        self.setLayout(layout)

    def update_graph(self, port=None):
        try:
            # 그래프 Y축 범위 설정 TODO (조정 필요)
            # for sensor in self.serial_manager.sensors:
            #     self.graph_sensor[sensor.port].graph_sensor.setYRange(min=self.save_graph_min, max=self.save_graph_max)

            # 특정 포트만 업데이트하거나 모든 포트 업데이트
            ports_to_update = [port] if port else [sensor.port for sensor in self.serial_manager.sensors]

            for port in ports_to_update:
                if port not in self.laser_plot_data:
                    self.laser_plot_data[port] = deque(maxlen=300)
                if port not in self.light_plot_data:
                    self.light_plot_data[port] = deque(maxlen=300)
                if not self.laser_plot_data[port] or len(self.laser_plot_data[port]) == 0:
                    continue
                if not self.light_plot_data[port] or len(self.light_plot_data[port]) == 0:
                    continue

                # X축 데이터 생성 - 시간에 따른 인덱스
                x_laser = list(range(len(self.laser_plot_data[port])))
                x_light = list(range(len(self.light_plot_data[port])))

                # Y축 레이저 센서 데이터 추출 - 안전 처리
                y_laser_values = []
                for point in self.laser_plot_data[port]:
                    try:
                        y_laser_value = float(point.distance)
                        y_laser_values.append(y_laser_value)
                    except (ValueError, AttributeError):
                        y_laser_values.append(0)

                # Y축 조도 센서 데이터 추출
                y_light_values = []
                for point in self.light_plot_data[port]:
                    try:
                        y_light_value = float(point.lux)
                        y_light_values.append(y_light_value)
                    except (ValueError, AttributeError):
                        y_light_values.append(0)

                # 데이터가 준비되면 그래프 업데이트
                if 0 < len(y_laser_values) == len(x_laser):
                    self.laser_plot_curve[port].setData(x_laser, y_laser_values)
                if 0 < len(y_light_values) == len(x_light):
                    self.light_plot_curve[port].setData(x_light, y_light_values)

        except Exception as e:
            print(f"그래프 업데이트 중 오류 발생: {e}")
            traceback.print_exc()

class SensorGraph(QWidget):
    def __init__(self, sensor_location, color):
        super().__init__()
        self.sensor_location = sensor_location
        self.color = color
        self.axis_directions = ["left", "bottom", "right", "top"]

        self.plot_widget = PlotWidget()
        self.plot = self.plot_widget.getPlotItem()
        self.plot.setTitle(f"{sensor_location} Sensor")
        self.plot.setLabel("bottom", "Time")
        self.plot.setLabel("left", "Laser Distance")
        self.plot.showAxis("right")
        self.plot.setLabel("right", "Light (lux)")
        for axis in self.axis_directions:
            self.plot.getAxis(axis).setPen(pg.mkPen('w'))  # 흰색 라벨

        # 레이저용 선 (왼쪽 Y축)
        self.laser_line = self.plot.plot(pen=pg.mkPen(self.color, width=1), name="Laser")
        # self.plot.vb.setYRange(0, 800)

        # 오른쪽 Y축용 ViewBox 생성
        self.right_viewbox = ViewBox()
        self.plot.scene().addItem(self.right_viewbox)
        self.plot.getAxis("right").linkToView(self.right_viewbox)
        self.right_viewbox.setXLink(self.plot)
        self.right_viewbox.setRange(yRange=(0, 4000))

        # 조도 센서용 선 (오른쪽 Y축)
        self.light_line = pg.PlotDataItem(pen=pg.mkPen('w', width=1), name="Light")
        self.right_viewbox.addItem(self.light_line)

        self.legend = self.plot.addLegend(offset=(30, 30))
        self.legend.addItem(self.laser_line, "Laser")
        self.legend.addItem(self.light_line, "Light")

        # 뷰 업데이트 연결
        self.plot.vb.sigResized.connect(self.update_views)

        # 범례 추가 및 수동 등록
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def update_views(self):
        """왼쪽 Y축과 오른쪽 Y축의 뷰 위치 동기화"""
        self.right_viewbox.setGeometry(self.plot.vb.sceneBoundingRect())
        self.right_viewbox.linkedViewChanged(self.plot.vb, self.right_viewbox.XAxis)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLightSensor()
    sys.exit(app.exec_())