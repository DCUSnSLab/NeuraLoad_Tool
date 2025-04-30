from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os

from analytics_data_organize import AnalyticsDataOrganize
from analytics_graph import AnalyticsGraph


class AnalyticsData(QWidget):
    def __init__(self):
        super().__init__()
        # 경로 설정
        self.path = './log'

        self.file_data = {}
        self.loc = []

        self.setupUI()
        self.load_file()

    def setupUI(self):
        # 로드한 파일 확인 테이블
        self.save_file_log = QListWidget()
        self.save_file_log.setSelectionMode(QAbstractItemView.MultiSelection)
        self.save_file_log.itemSelectionChanged.connect(self.select_file)

        # x축 부분 라벨과 콤보 박스
        self.x_text = QLabel('x: ')
        self.x_cb = QComboBox()
        self.x_cb.addItems(['무게'])
        self.x_cb.adjustSize()
        self.x_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # y축 부분 라벨과 콤보 박스
        self.y_text = QLabel('y: ')
        self.y_cb = QComboBox()
        self.y_cb.addItems(['거리 변화량', '거리값'])
        self.y_cb.adjustSize()
        self.y_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.checkbox = []
        layout_checkboxtcb = QHBoxLayout()
        for i in range(1,10):
            checkbox = QCheckBox(str(i), self)
            checkbox.stateChanged.connect(self.loc_cb)
            layout_checkboxtcb.addWidget(checkbox)
            self.checkbox.append(checkbox)

        # 그래프 시작 버튼
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start)

        # 그래프 공간 임의 제작
        self.graph_space = QMdiArea()
        self.graph_space.setMinimumHeight(500)

        # gui 배치
        layout_xy = QHBoxLayout()
        layout_xy.addWidget(self.x_text)
        layout_xy.addWidget(self.x_cb)
        layout_xy.addWidget(self.y_text)
        layout_xy.addWidget(self.y_cb)

        layout_group = QGroupBox('무게의 위치 선택')
        layout_group.setLayout(layout_checkboxtcb)

        layout_setting = QVBoxLayout()
        layout_setting.addLayout(layout_xy)
        layout_setting.addWidget(layout_group)
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
        self.save_file_log.clear()

        if not os.path.isdir(self.path):
            self.save_file_log.addItem('유효하지 않은 경로')
            return

        for name in os.listdir(self.path):
            if name.endswith('.bin'):
                file_path = os.path.join(name)
                self.save_file_log.addItem(file_path)

    def select_file(self):
        self.file_data.clear()
        self.file_data = [item.text() for item in self.save_file_log.selectedItems()]

    def loc_cb(self):
        self.loc.clear()
        self.loc = [i for i, cb in enumerate(self.checkbox) if cb.isChecked()]

    # 시작 버튼
    def start(self):
        '''
        x:
        0 = 무게

        y:
        0 = 데이터 변화량
        1 = 데이터 값

        self.file_data = 선택한 파일 경로
        self.loc = 무게 위치 입력 저장
        '''

        x = self.x_cb.currentIndex()
        y = self.y_cb.currentIndex()

        if len(self.loc) == 0:
            QMessageBox.warning(self, 'Warning', '확인할 무게 위치를 선택해주세요.')
        else:
            organized_data = AnalyticsDataOrganize(self.path, x, y, self.file_data, self.loc)

            graph = AnalyticsGraph(organized_data.total_common)

            subwindow = QMdiSubWindow()
            subwindow.setWidget(graph)

            self.graph_space.addSubWindow(subwindow)
            subwindow.show()