from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os

from analytics_data_graph import AnalyticsDataGraph

class Analytics(QWidget):
    def __init__(self):
        super().__init__()
        self.file_data = {}
        self.loc = []

        self.setupUI()

    def setupUI(self):
        # 파일 업로드 버튼
        self.upload_btn = QPushButton('Data load', self)
        self.upload_btn.clicked.connect(self.data_load)

        # 로드한 파일 확인 테이블
        self.save_file_log = QTableWidget()
        self.save_file_log.setColumnCount(1)
        self.save_file_log.setHorizontalHeaderLabels(['Saved files'])
        self.save_file_log.horizontalHeader().setStretchLastSection(True)
        self.save_file_log.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # x축 부분 라벨과 콤보 박스
        self.x_text = QLabel('x: ')
        self.x_cb = QComboBox()
        self.x_cb.addItems(['무게'])
        self.x_cb.adjustSize()
        self.x_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # y축 부분 라벨과 콤보 박스
        self.y_text = QLabel('y: ')
        self.y_cb = QComboBox()
        self.y_cb.addItems(['데이터 변화량', '데이터 값'])
        self.y_cb.adjustSize()
        self.y_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 확인할 무게 위치 설정을 위한 라벨과 입력창
        self.location_text = QLabel('Location: ')
        self.location = QLineEdit()
        self.location.textEdited.connect(self.location_save)

        # 그래프 시작 버튼
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start)

        # 그래프 공간 임의 제작
        self.graph_space = QLabel()

        # gui 배치
        layout_x = QHBoxLayout()
        layout_x.addWidget(self.x_text)
        layout_x.addWidget(self.x_cb)

        layout_y = QHBoxLayout()
        layout_y.addWidget(self.y_text)
        layout_y.addWidget(self.y_cb)

        layout_loc = QHBoxLayout()
        layout_loc.addWidget(self.location_text)
        layout_loc.addWidget(self.location)

        layout1 = QVBoxLayout()
        layout1.addWidget(self.upload_btn)
        layout1.addWidget(self.save_file_log)
        layout1.addLayout(layout_x)
        layout1.addLayout(layout_y)
        layout1.addLayout(layout_loc)
        layout1.addWidget(self.start_btn)

        layout_widget = QWidget()
        layout_widget.setLayout(layout1)
        layout_widget.setFixedWidth(500)

        layout2 = QHBoxLayout()
        layout2.addWidget(layout_widget, alignment=Qt.AlignLeft)
        layout2.addWidget(self.graph_space)

        self.setLayout(layout2)

    # 데이터 업로드
    def data_load(self):
        self.file_data.clear()

        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*)", options=options)

        if files:
            for file in files:
                if file not in self.file_data:
                    self.file_data[file] = None
                    self.add_file_log(file)

    # 파일 로그 업로드
    def add_file_log(self, file):
        filename = os.path.basename(file)

        row = self.save_file_log.rowCount()
        self.save_file_log.insertRow(row)
        self.save_file_log.setItem(row, 0, QTableWidgetItem(filename))

    # 그래프 구현을 위한 무게 위치 선정
    def location_save(self):
        self.loc.clear()
        raw_text = self.location.text().strip()
        texts = [text.strip() for text in raw_text.split(",") if text.strip()]

        for text in texts:
            if 0 < int(text) < 10:
                self.loc.append(text)
            else:
                QMessageBox.warning(self, 'Warning', '1에서 9까지의 숫자를 입력해주세요.')

    # 시작 버튼
    def start(self):
        '''
        x:
        0 = 무게

        y:
        0 = 데이터 변화량
        1 = 데이터 값

        self.file_data = 업로드한 파일 경로
        self.loc = 무게 위치 입력 저장
        '''

        x = self.x_cb.currentIndex()
        y = self.y_cb.currentIndex()

        if len(self.loc) > 0:
            AnalyticsDataGraph(x, y, self.file_data, self.loc)
        else:
            QMessageBox.warning(self, 'Warning', '확인할 무게 위치를 입력해주세요.')