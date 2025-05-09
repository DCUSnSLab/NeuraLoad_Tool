from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os

from analytics_algo_organize import AnalyticsAlgoOrganize

class Analytics(QWidget):
    def __init__(self):
        super().__init__()
        # 경로 설정
        self.path = './log'
        self.scenario_files = [name for name in os.listdir(self.path)
                               if os.path.isdir(os.path.join(self.path, name))]

        self.file_data = {}

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
        self.file_data.clear()
        self.file_data = [item.text() for item in self.save_file_log.selectedItems()]

    def loc_cb(self):
        self.loc.clear()
        self.loc = [i for i, cb in enumerate(self.checkbox) if cb.isChecked()]

        # 시작 버튼
    def start(self):
        if self.file_data:
            organized_data = AnalyticsAlgoOrganize(self.file_data)

            subwindow = QMdiSubWindow()
            subwindow.setWidget(organized_data)

            self.graph_space.addSubWindow(subwindow)
            subwindow.show()
        else:
            QMessageBox.warning(self, 'Warning', '파일을 선택해주세요.')