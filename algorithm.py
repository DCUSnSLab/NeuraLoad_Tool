import os
import sys
import ast
import subprocess
import json
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class Algorithm(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager  # SerialManager 인스턴스 저장
        self.weight_total = [0] * 9
        self.weight_location = [0] * 9
        self.selected_names = []
        self.algorithm_processes = {}  # 실행 중인 알고리즘 프로세스 저장
        self.algorithm_results = {}    # 알고리즘 결과 저장
        self.setupUI()
        self.setup()

        self.result_timer = QTimer(self)
        self.result_timer.timeout.connect(self.check_algorithm_results)
        self.result_timer.start(500)  # 500ms마다 결과 확인

    def setupUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        self.load_files()

        self.start_btn = QPushButton('Run the selected algorithm', self)
        self.start_btn.clicked.connect(self.start)

        self.reset_btn = QPushButton('Reset', self)
        self.reset_btn.clicked.connect(self.reset)

        self.all_btn = QPushButton('Run all', self)
        self.all_btn.clicked.connect(self.run_all)

        self.actual_weight_text = QLabel('Actual Weight:')
        self.actual_weight_output = QLabel("-")
        self.actual_weight_kg = QLabel("kg")

        self.actual_location_text = QLabel('Actual Location:')
        self.actual_location_output = QLabel("-")
        self.weight_update()

        self.weight_table = QTableWidget()
        self.weight_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def load_files(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]
        self.files = []
        self.checkboxes = []

        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files.append((file_name, full_path))

            checkbox = QCheckBox(file_name)
            self.checkbox_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

    def start(self):
        self.selected_names = []
        self.algorithm_processes = {}
        self.algorithm_results = {}

        # 선택된 알고리즘 파일 확인
        for checkbox, (file_name, full_path) in zip(self.checkboxes, self.files):
            if checkbox.isChecked():
                self.selected_names.append(file_name)

        if not self.selected_names:
            QMessageBox.warning(self, "알림", "실행할 알고리즘을 선택해주세요.")
            return

        # 테이블 설정
        self.weight_table.setColumnCount(len(self.selected_names))
        self.weight_table.setRowCount(3)
        self.weight_table.setVerticalHeaderItem(0, QTableWidgetItem('추정 무게'))
        self.weight_table.setVerticalHeaderItem(1, QTableWidgetItem('추정 위치'))
        self.weight_table.setVerticalHeaderItem(2, QTableWidgetItem('오차율'))

        for i, name in enumerate(self.selected_names):
            self.weight_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))

        self.weight_table.resizeColumnsToContents()

        # 선택된 알고리즘 별도 프로세스로 실행
        self.run_algorithms_as_subprocess()

    def run_algorithms_as_subprocess(self):
        """선택된 알고리즘을 별도 프로세스로 실행"""
        # serial_manager.latest_candidate_window가 없거나 비어있으면 경고 표시
        if not hasattr(self.serial_manager, 'latest_candidate_window') or not self.serial_manager.latest_candidate_window:
            QMessageBox.warning(self, "데이터 없음", "센서 데이터가 없습니다. 실험을 먼저 시작해주세요.")
            return

        # latest_candidate_window를 JSON으로 직렬화
        try:
            # 직접 객체를 직렬화할 수 없는 경우 필요한 변환을 수행
            serializable_data = {}
            for port, data in self.serial_manager.latest_candidate_window.items():
                # datetime 객체를 문자열로 변환하여 serializable하게 만듦
                serializable_port_data = {k: (v.isoformat() if k == 'timestamp_dt' else v)
                                         for k, v in data.items()}
                serializable_data[port] = serializable_port_data

            sensor_data_json = json.dumps(serializable_data)
        except Exception as e:
            QMessageBox.critical(self, "데이터 변환 오류", f"센서 데이터 변환 중 오류가 발생했습니다: {str(e)}")
            return

        # 선택된 각 알고리즘에 대해 별도 프로세스 실행
        for file_name, full_path in self.files:
            if file_name in self.selected_names:
                cmd = [sys.executable, 'run_algorithm.py', full_path, sensor_data_json]

                # 별도 프로세스로 알고리즘 실행
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    # 프로세스 저장
                    self.algorithm_processes[file_name] = process
                    print(f"{file_name} 알고리즘이 별도 프로세스로 실행되었습니다.")
                except Exception as e:
                    QMessageBox.critical(self, "프로세스 실행 오류", f"{file_name} 실행 중 오류: {str(e)}")

    def check_algorithm_results(self):
        """실행 중인 알고리즘 프로세스 결과 확인"""
        finished_algos = []

        for file_name, process in self.algorithm_processes.items():
            # 프로세스가 완료되었는지 확인
            if process.poll() is not None:
                try:
                    # 프로세스 출력 읽기
                    stdout, stderr = process.communicate()

                    if process.returncode != 0:
                        # 오류 발생
                        self.algorithm_results[file_name] = {
                            "error": f"Process error: {stderr}"
                        }
                    else:
                        # 정상 완료 - JSON 결과 파싱
                        try:
                            data = ast.literal_eval(stdout)
                            print(data)
                            print(data["weight"])
                            self.algorithm_results[file_name] = {"weight": data["weight"], "position": data["position"]}
                        except json.JSONDecodeError:
                            self.algorithm_results[file_name] = {
                                "error": f"JSON parsing error: {stdout}"
                            }

                except Exception as e:
                    self.algorithm_results[file_name] = {
                        "error": f"Error processing result: {str(e)}"
                    }

                # 완료된 알고리즘 목록에 추가
                finished_algos.append(file_name)

        # 완료된 알고리즘 프로세스 정리
        for file_name in finished_algos:
            del self.algorithm_processes[file_name]
            self.update_result_table(file_name)

    def update_result_table(self, file_name):
        """알고리즘 결과로 테이블 업데이트"""
        if file_name not in self.selected_names:
            return

        result = self.algorithm_results.get(file_name, {})
        col_index = self.selected_names.index(file_name)

        if "error" in result:
            # 오류 메시지 표시
            for row in range(3):
                self.weight_table.setItem(row, col_index, QTableWidgetItem("Error"))
            QMessageBox.critical(self, "알고리즘 오류", f"{file_name}: {result['error']}")
            return

        try:
            # 무게 정보 표시
            if "weight" in result:
                weight_item = QTableWidgetItem(str(result["weight"]))
                self.weight_table.setItem(0, col_index, weight_item)

            # 위치 정보 표시
            if "position" in result:
                position_item = QTableWidgetItem(str(result["position"]))
                self.weight_table.setItem(1, col_index, position_item)

            # 오차율 계산 및 표시
            if "weight" in result and isinstance(self.weight_total, (int, float)):
                try:
                    error_rate = abs(result["weight"] - self.weight_total) / max(1, self.weight_total) * 100
                    error_item = QTableWidgetItem(f"{error_rate:.2f}%")
                    self.weight_table.setItem(2, col_index, error_item)
                except (TypeError, ValueError):
                    error_item = QTableWidgetItem("N/A")
                    self.weight_table.setItem(2, col_index, error_item)

        except Exception as e:
            QMessageBox.warning(self, "결과 처리 오류", f"{file_name} 결과 처리 중 오류 발생: {str(e)}")

    def reset(self):
        """모든 설정 초기화"""
        # 체크박스 초기화
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

        # 선택된 알고리즘 목록 초기화
        self.selected_names.clear()

        # 실행 중인 프로세스 종료
        for process in self.algorithm_processes.values():
            process.terminate()

        self.algorithm_processes.clear()
        self.algorithm_results.clear()

        # 결과 테이블 초기화
        self.weight_table.clear()
        self.weight_table.setColumnCount(0)
        self.weight_table.setRowCount(0)

    def run_all(self):
        """모든 알고리즘 실행"""
        # 모든 체크박스 선택
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

        # 선택된 알고리즘 목록 초기화 및 모든 알고리즘 추가
        self.selected_names = []
        for file_name, _ in self.files:
            self.selected_names.append(file_name)

        # 테이블 설정
        self.weight_table.setColumnCount(len(self.selected_names))
        self.weight_table.setRowCount(3)
        self.weight_table.setVerticalHeaderItem(0, QTableWidgetItem('추정 무게'))
        self.weight_table.setVerticalHeaderItem(1, QTableWidgetItem('추정 위치'))
        self.weight_table.setVerticalHeaderItem(2, QTableWidgetItem('오차율'))

        for i, name in enumerate(self.selected_names):
            self.weight_table.setHorizontalHeaderItem(i, QTableWidgetItem(name))

        self.weight_table.resizeColumnsToContents()

        # 모든 알고리즘 별도 프로세스로 실행
        self.run_algorithms_as_subprocess()

    def weight_update(self):
        """무게 정보 업데이트"""
        # 무게 총합 계산
        if isinstance(self.weight_total, list):
            total_weight = sum(self.weight_total)
        else:
            total_weight = self.weight_total

        # 무게 위치 처리
        all_weight_location = list(filter(lambda x: self.weight_location[x] == 1, range(len(self.weight_location))))
        all_weight_location = [i+1 for i in all_weight_location]

        if not all_weight_location:
            self.actual_location_output.setText("0")
        else:
            self.actual_location_output.setText(str(all_weight_location))

        self.actual_weight_output.setText(str(total_weight))

    def set_weight(self, weight_a):
        """무게 정보 설정"""
        self.weight_total = weight_a
        self.weight_location = [0] * len(weight_a)
        for i in range(len(self.weight_total)):
            if self.weight_total[i] > 0:
                self.weight_location[i] = 1
        self.weight_update()

    def update_data(self, port, data):
        """데이터 업데이트 - Experiment에서 데이터 전달받음"""
        pass

    def setup(self):
        """UI 레이아웃 설정"""
        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)

        weight_layout1 = QHBoxLayout()
        weight_layout1.addWidget(self.actual_weight_text)
        weight_layout1.addWidget(self.actual_weight_output)
        weight_layout1.addWidget(self.actual_weight_kg)
        weight_layout1.addStretch()
        weight_layout1.setSpacing(10)

        weight_layout2 = QHBoxLayout()
        weight_layout2.addWidget(self.actual_location_text)
        weight_layout2.addWidget(self.actual_location_output)
        weight_layout2.addStretch()
        weight_layout2.setSpacing(10)

        layout = QVBoxLayout()
        layout.addLayout(weight_layout1)
        layout.addLayout(weight_layout2)
        layout.addWidget(self.weight_table)

        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addWidget(self.all_btn)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

    def closeEvent(self, event):
        """창이 닫힐 때 실행 중인 프로세스 종료"""
        for process in self.algorithm_processes.values():
            try:
                process.terminate()
            except:
                pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 메인 함수에서 Algorithm 단독 실행 시 SerialManager 객체 필요
    from arduino_manager import SerialManager
    serial_manager = SerialManager(debug_mode=True)
    serial_manager.start_threads()
    ex = Algorithm(serial_manager)
    ex.show()
    sys.exit(app.exec_())
