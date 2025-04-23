from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os

class Analytics(QWidget):
    file_data = {}
    clicked_file_list = []

    def __init__(self):
        super().__init__()

        self.setupUI()

    def setupUI(self):
        # 파일 업로드 버튼
        self.upload_btn = QPushButton('Uploading data files', self)
        self.upload_btn.clicked.connect(self.upload)

        # 업로드한 파일 확인 테이블
        self.save_file_log = QTableWidget()
        self.save_file_log.setColumnCount(1)
        self.save_file_log.setHorizontalHeaderLabels(['Saved files'])
        self.save_file_log.horizontalHeader().setStretchLastSection(True)
        self.save_file_log.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.save_file_log.itemSelectionChanged.connect(self.clicked_file)

        # x축 부분 라벨과 콤보박스
        self.x_text = QLabel('x: ')
        self.x_text_cb = QComboBox()
        self.x_text_cb.addItems(['', '추가'])
        self.x_text_cb.adjustSize()
        self.x_text_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # y축 부분 라벨과 콤보박스
        self.y_text = QLabel('y: ')
        self.y_text_cb = QComboBox()
        self.y_text_cb.addItems(['', '추가'])
        self.y_text_cb.adjustSize()
        self.y_text_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 그래프 시작 버튼
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start)

        # 그래프 공간 임의 제작
        self.graph_space = QLabel()

        # gui 배치
        layout_x = QHBoxLayout()
        layout_x.addWidget(self.x_text)
        layout_x.addWidget(self.x_text_cb)

        layout_y = QHBoxLayout()
        layout_y.addWidget(self.y_text)
        layout_y.addWidget(self.y_text_cb)

        layout1 = QVBoxLayout()
        layout1.addWidget(self.upload_btn)
        layout1.addWidget(self.save_file_log)
        layout1.addLayout(layout_x)
        layout1.addLayout(layout_y)
        layout1.addWidget(self.start_btn)

        layout_widget = QWidget()
        layout_widget.setLayout(layout1)
        layout_widget.setFixedWidth(500)

        layout2 = QHBoxLayout()
        layout2.addWidget(layout_widget, alignment=Qt.AlignLeft)
        layout2.addWidget(self.graph_space)

        self.setLayout(layout2)

    def upload(self):
        self.file_data.clear()

        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*)", options=options)

        if files:
            for file in files:
                if file not in self.file_data:
                    self.file_data[file] = None
                    self.add_file_log(file)

    def add_file_log(self, file):
        filename = os.path.basename(file)

        row = self.save_file_log.rowCount()
        self.save_file_log.insertRow(row)
        self.save_file_log.setItem(row, 0, QTableWidgetItem(filename))

    def clicked_file(self):
        self.clicked_file_list.clear()
        selected_rows = set()
        for item in self.save_file_log.selectedItems():
            selected_rows.add(item.row())

        for row in selected_rows:
            item = self.save_file_log.item(row, 0)
            if item:
                self.clicked_file_list.append(item.text())

    def start(self):
        pass