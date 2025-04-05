import os
import sys
import importlib.util
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from collections import deque
from arduino_manager import SerialThread, get_arduino_ports
from experiment import Experiment

class Algorithm(QWidget):
    def __init__(self, parent_experiment=None):
        super().__init__()
        self.threads = []
        self.ports = get_arduino_ports()
        self.port_location = {}
        self.port_colors = {}
        self.port_index = {}
        self.plot_curve = {}
        self.plot_data = {}
        self.plot_curve_change = {}
        self.plot_change = {}
        self.parent_experiment = parent_experiment  # 실험 클래스 참조 저장

        self.weight_a = [0] * 9
        self.selected_algorithm = None
        self.algorithm_instance = None

        self.setting()
        self.setupUI()
        self.setup()

    def set_weight(self, weight):
        self.weight_a = weight.copy()

    def setting(self):
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
            self.port_index[port] = i

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        self.load_files()

        self.start_btn = QPushButton('선택한 알고리즘 실행', self)
        self.start_btn.clicked.connect(self.start)

        self.reset_btn = QPushButton('리셋', self)
        self.reset_btn.clicked.connect(self.reset)

        self.stop_btn = QPushButton('정지(K)', self)
        self.stop_btn.clicked.connect(self.stop)

        self.restart_btn = QPushButton('재시작(L)', self)
        self.restart_btn.clicked.connect(self.restart)

        self.sensor_table = QTableWidget()
        self.sensor_table.setColumnCount(len(self.ports))
        self.sensor_table.setRowCount(1)
        for i, port in enumerate(self.ports):
            name = self.port_location.get(port, "")
            self.sensor_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
        self.sensor_table.setVerticalHeaderLabels(['value'])

        self.logging = QTableWidget()
        self.logging.setColumnCount(3)
        self.logging.setHorizontalHeaderLabels(['무게', '위치', '로그'])
        self.logging.setMinimumHeight(150)
        self.logging.setMinimumWidth(150)
        self.logging.horizontalHeader().setStretchLastSection(True)

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

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #F2F2F2;")
        self.log_output.append("알고리즘 도구가 시작되었습니다. 실행할 알고리즘을 선택하세요.")

    def load_files(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        self.files = []
        self.checkboxes = []

        # Algorithm 디렉토리에서 파이썬 파일 찾기
        try:
            for file_name in os.listdir(folder):
                # .py 확장자를 가진 파일만 필터링
                if file_name.endswith('.py'):
                    full_path = os.path.join(folder, file_name)
                    self.files.append((file_name, full_path))

                    checkbox = QCheckBox(file_name)
                    # 한 번에 하나의 알고리즘만 선택되도록 처리
                    checkbox.clicked.connect(lambda checked, name=file_name: self.handle_checkbox_click(name, checked))
                    self.checkbox_layout.addWidget(checkbox)

                    self.checkboxes.append(checkbox)

            # 파일이 없을 경우 안내 메시지 추가
            if not self.files:
                label = QLabel("사용 가능한 알고리즘 파일이 없습니다.")
                self.checkbox_layout.addWidget(label)
        except Exception as e:
            label = QLabel(f"오류 발생: {str(e)}")
            self.checkbox_layout.addWidget(label)

    def handle_checkbox_click(self, name, checked):
        """체크박스 클릭 이벤트 처리"""
        if checked:
            # 다른 모든 체크박스 해제
            for checkbox in self.checkboxes:
                if checkbox.text() != name:
                    checkbox.setChecked(False)
            self.selected_algorithm = name
            self.log_output.append(f"알고리즘 '{name}'이(가) 선택되었습니다.")
        else:
            if self.selected_algorithm == name:
                self.selected_algorithm = None

    def load_algorithm_module(self, algorithm_name):
        """파이썬 파일을 동적으로 로드하여 알고리즘 인스턴스 생성"""
        try:
            folder = os.path.join(os.getcwd(), 'Algorithm')
            module_path = os.path.join(folder, algorithm_name)
            
            # 파일 경로에서 모듈 이름 추출
            module_name = os.path.splitext(algorithm_name)[0]
            
            # 모듈 스펙 생성
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                raise ImportError(f"모듈을 찾을 수 없습니다: {module_path}")
                
            # 모듈 로드
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 모듈 내 클래스 찾기 - 특별히 RandomForestPredictor 클래스를 찾음
            if module_name == 'RandomForestPredictor':
                if hasattr(module, 'RandomForestPredictor'):
                    class_obj = getattr(module, 'RandomForestPredictor')
                    return class_obj()
                
            # 다른 모듈의 경우 일반적인 방법으로 클래스 찾기
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and not attr_name.startswith('_') and attr_name != 'AlgorithmBase':
                    try:
                        instance = attr()
                        self.log_output.append(f"클래스 {attr_name} 로드 완료")
                        return instance
                    except Exception as class_err:
                        self.log_output.append(f"클래스 {attr_name} 인스턴스화 실패: {str(class_err)}")
            
            self.log_output.append(f"모듈 {module_name}에서 적합한 알고리즘 클래스를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            self.log_output.append(f"알고리즘 로드 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def update_data(self, port, data):
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

            self.plot_curve[port].setData(x, y)
            self.plot_curve_change[port].setData(x, change)

            location = self.port_index[port]
            self.sensor_table.setItem(0, location, QTableWidgetItem(data))

            current_row = self.logging.rowCount()
            self.logging.insertRow(current_row)
            self.logging.setItem(current_row, 0, QTableWidgetItem(str(self.weight_a)))

            name = self.port_location.get(port, "")
            self.logging.setItem(current_row, 1, QTableWidgetItem(name))

            self.logging.setItem(current_row, 2, QTableWidgetItem(data))
            self.logging.scrollToBottom()

    def start(self):
        """선택한 알고리즘 실행"""
        if not self.selected_algorithm:
            self.log_output.append("먼저 알고리즘을 선택하세요.")
            return
        
        self.log_output.append(f"알고리즘 '{self.selected_algorithm}' 실행 중...")
        
        # 특별한 처리 - LaserDataProcessor 클래스를 위한 처리
        if self.selected_algorithm == 'Estimation_mass_algorithm.py':
            try:
                from Algorithm.Estimation_mass_algorithm import LaserDataProcessor
                self.algorithm_instance = LaserDataProcessor()
                # 레이저 변화량 처리
                input_data = self.collect_sensor_data()
                if not input_data or 'laser_values' not in input_data:
                    self.log_output.append("센서 데이터를 수집할 수 없습니다.")
                    return
                
                # 레이저 데이터 처리
                laser_values = input_data['laser_values']
                for i, value in enumerate(laser_values):
                    if i < 4:  # 최대 4개의 포트만 처리
                        # 이전 값이 있는 경우 변화량 계산, 없으면 0
                        change = 0
                        if self.algorithm_instance.laser_changes[i]:
                            change = value - self.algorithm_instance.laser_changes[i][-1] if self.algorithm_instance.laser_changes[i] else 0
                        else:
                            self.algorithm_instance.laser_changes[i] = []
                        
                        # 변화량 처리
                        result = self.algorithm_instance.process_data(i, change)
                        if result:
                            self.display_results(result)
                            break
                    
            except Exception as e:
                self.log_output.append(f"LaserDataProcessor 실행 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return
        
        # RandomForestPredictor 특별 처리
        elif self.selected_algorithm == 'RandomForestPredictor.py':
            try:
                # 직접 파일 경로를 통한 패키지 참조 방식 사용
                sys.path.append(os.path.join(os.getcwd(), 'Algorithm'))
                from RandomForestPredictor import RandomForestPredictor
                self.algorithm_instance = RandomForestPredictor()
                
                # 센서 데이터 수집
                input_data = self.collect_sensor_data()
                if not input_data:
                    self.log_output.append("센서 데이터를 수집할 수 없습니다.")
                    return
                
                # 알고리즘 실행
                results = self.algorithm_instance.execute(input_data)
                self.display_results(results)
                
            except Exception as e:
                self.log_output.append(f"RandomForestPredictor 로드 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return
        
        # 일반적인 알고리즘 처리 방식
        # 알고리즘 모듈 로드
        self.algorithm_instance = self.load_algorithm_module(self.selected_algorithm)
        
        if self.algorithm_instance is None:
            self.log_output.append("알고리즘 로드에 실패했습니다.")
            return
        
        # 센서 데이터 수집 (parent_experiment가 있을 경우 사용)
        input_data = self.collect_sensor_data()
        
        if not input_data:
            self.log_output.append("센서 데이터를 수집할 수 없습니다.")
            return
        
        # 알고리즘 실행
        try:
            results = self.algorithm_instance.execute(input_data)
            self.display_results(results)
        except Exception as e:
            self.log_output.append(f"알고리즘 실행 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def collect_sensor_data(self):
        """실험 클래스에서 센서 데이터 수집"""
        data = {}
        
        # parent_experiment가 있는 경우 데이터 수집
        if self.parent_experiment and hasattr(self.parent_experiment, 'serial_manager'):
            # SerialManager 인스턴스 접근
            sm = self.parent_experiment.serial_manager
            
            # 센서 데이터 수집
            if hasattr(sm, 'threads'):
                laser_values = []
                
                for thread in sm.threads:
                    if hasattr(thread, 'databuf') and not thread.databuf.empty():
                        try:
                            # 큐에서 데이터 가져오기 (복제 후 다시 넣기)
                            data_point = thread.databuf.get()
                            thread.databuf.put(data_point)  # 데이터 다시 넣기
                            
                            # 데이터 포인트에서 값 추출
                            if isinstance(data_point, tuple) and len(data_point) > 1:
                                value = data_point[1]  # 두 번째 요소 (값)
                                laser_values.append(value)
                        except Exception as e:
                            self.log_output.append(f"데이터 수집 중 오류: {str(e)}")
                
                # 필요한 레이저 값 수 확인
                if len(laser_values) < 4:
                    # 부족한 값 0으로 채우기
                    laser_values.extend([0] * (4 - len(laser_values)))
                elif len(laser_values) > 4:
                    # 초과 값 자르기
                    laser_values = laser_values[:4]
                
                data['laser_values'] = laser_values
                self.log_output.append(f"수집된 센서 데이터: {laser_values}")
        
        # 데이터가 없는 경우 더미 데이터 생성
        if not data:
            self.log_output.append("더미 데이터를 사용합니다.")
            data['laser_values'] = [600, 650, 600, 650]  # 더미 데이터
        
        return data

    def display_results(self, results):
        """알고리즘 실행 결과 표시"""
        self.log_output.append("\n===== 알고리즘 실행 결과 =====")

        if isinstance(results, dict):
            # 무게와 위치 정보를 표에 추가
            if 'weight' in results:
                current_row = self.logging.rowCount()
                self.logging.insertRow(current_row)
                self.logging.setItem(current_row, 0, QTableWidgetItem(str(results['weight'])))

                # position이 있으면 위치 탭에 추가
                if 'position' in results:
                    self.logging.setItem(current_row, 1, QTableWidgetItem(str(results['position'])))

                # 종합 정보를 로그 탭에 추가
                log_text = f"입력값: {results.get('input_values', 'N/A')}"
                self.logging.setItem(current_row, 2, QTableWidgetItem(log_text))
                self.logging.scrollToBottom()

            # 전체 결과는 로그 출력에도 표시
            for key, value in results.items():
                self.log_output.append(f"{key}: {value}")
        else:
            self.log_output.append(str(results))

        self.log_output.append("==============================\n")

    def reset(self):
        """알고리즘 선택 초기화"""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
        self.selected_algorithm = None
        self.algorithm_instance = None
        self.log_output.clear()
        self.log_output.append("알고리즘 선택이 초기화되었습니다.")

    def stop(self):
        for thread in self.threads:
            thread.pause()
        QCoreApplication.processEvents()

    def restart(self):
        for thread in self.threads:
            thread.resume()

    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('현재 사용 가능한 알고리즘')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        btn_layout1 = QHBoxLayout()
        btn_layout1.addWidget(self.stop_btn)
        btn_layout1.addWidget(self.restart_btn)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addLayout(btn_layout1)
        layout1.addWidget(self.logging)

        layout3 = QVBoxLayout()
        layout3.addWidget(self.log_output)

        layout4 = QHBoxLayout()
        layout4.addLayout(layout1)
        layout4.addLayout(layout3)

        self.setLayout(layout4)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = Algorithm()
   sys.exit(app.exec_())
