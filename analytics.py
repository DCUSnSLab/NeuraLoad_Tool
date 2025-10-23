import datetime
import os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from analytics_algo_organize import AnalyticsAlgoOrganize
from experiment import finalize_inprogress_files
from laser_light_sensor_file import LaserLightSensorFile


class Analytics(QWidget):
    def __init__(self, experiment_class):
        super().__init__()
        self.experiment_class = experiment_class
        # 경로 설정
        self.path = './log'
        self.scenario_files = [name for name in os.listdir(self.path)
                               if os.path.isdir(os.path.join(self.path, name))]

        self.selected_file_paths = {}

        self.setupUI()
        self.load_file()

    def setupUI(self):
        # 로드한 파일 확인 테이블
        self.save_file_log = QListWidget()
        # self.save_file_log.setSelectionMode(QAbstractItemView.MultiSelection)
        self.save_file_log.setSelectionMode(QAbstractItemView.SingleSelection)
        self.save_file_log.itemSelectionChanged.connect(self.select_file)

        # self.scenario_text = QLabel('시나리오 선택: ')
        # self.scenario_cb = QComboBox()
        # self.scenario_cb.addItems(self.scenario_files)
        # self.scenario_cb.adjustSize()
        # self.scenario_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.scenario_cb.currentIndexChanged.connect(self.load_file)

        # 그래프 시작 버튼
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start)

        # 파일 목록 재설정 및 현재 데이터 업데이트
        self.refresh_btn = QPushButton('Refresh', self)
        self.refresh_btn.clicked.connect(self.refresh_list)

        # 그래프 공간 임의 제작
        self.graph_space = QMdiArea()
        self.graph_space.setMinimumHeight(500)

        # gui 배치
        # layout = QHBoxLayout()
        # layout.addWidget(self.scenario_text)
        # layout.addWidget(self.scenario_cb)

        layout_setting = QVBoxLayout()
        # layout_setting.addLayout(layout)
        layout_setting.addWidget(self.start_btn)
        layout_setting.addWidget(self.refresh_btn)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.save_file_log)
        layout1.addSpacing(20)
        layout1.addLayout(layout_setting)

        layout_widget = QWidget()
        layout_widget.setLayout(layout1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(layout_widget)
        splitter.addWidget(self.graph_space)

        layout2 = QVBoxLayout()
        layout2.addWidget(splitter)

        self.setLayout(layout2)

    def refresh_list(self):
        # 자동 저장을 일시 중지한 뒤, 최신화 작업을 수행하고 다시 자동 저장을 시작
        self.experiment_class.auto_save_timer.stop()
        finalize_inprogress_files()
        self.experiment_class.auto_save_timer.start(1000)
        print(f'자동 저장 임시 파일 생성: {datetime.datetime.now().strftime("raw_data_%Y-%m-%d.bin.inprogress")}')
        self.load_file()

    # 파일 불러오기
    def load_file(self):
        # select = self.scenario_cb.currentText()
        # path = os.path.join(self.path, select)

        self.save_file_log.clear()

        if not os.path.isdir(self.path):
            self.save_file_log.addItem('유효하지 않은 경로')
            return

        for name in os.listdir(self.path):
            if name.endswith('.bin'):
                file_path = os.path.join(self.path, name)
                rel_path = os.path.relpath(file_path, self.path)
                self.save_file_log.addItem(rel_path)

    def select_file(self):
        self.selected_file_paths.clear()
        self.selected_file_paths = [item.text() for item in self.save_file_log.selectedItems()]

    def loc_cb(self):
        self.loc.clear()
        self.loc = [i for i, cb in enumerate(self.checkbox) if cb.isChecked()]

        # 시작 버튼

    def start(self):
        if self.selected_file_paths:
            if self.selected_file_paths[0].startswith('raw_data'):
                organized_data = LaserLightSensorFile(self.selected_file_paths[0])

                organized_scatter_data = LaserLightSensorFile(self.selected_file_paths[0], 'scatter')
                subwindow_scatter = QMdiSubWindow()
                subwindow_scatter.setWidget(organized_scatter_data)
                subwindow_scatter.setWindowTitle(str(self.selected_file_paths))
                self.graph_space.addSubWindow(subwindow_scatter)   # 이 부분 추가 필요
                subwindow_scatter.show()
            else:
                organized_data = AnalyticsAlgoOrganize(self.selected_file_paths)

            subwindow = QMdiSubWindow()
            subwindow.setWidget(organized_data)
            subwindow.setWindowTitle(str(self.selected_file_paths))

            self.graph_space.addSubWindow(subwindow)
            subwindow.show()
        else:
            QMessageBox.warning(self, 'Warning', '파일을 선택해주세요.')
