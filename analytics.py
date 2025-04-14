from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QTableWidget, QAbstractItemView, QLabel, \
    QComboBox, QHBoxLayout

class Analytics(QWidget):
    def __init__(self):
        super().__init__()
        self.setupUI()
        self.setup()

    def setupUI(self):
        # 파일 업로드 버튼
        self.upload_btn = QPushButton('Uploading data files', self)
        self.upload_btn.clicked.connect(self.upload)

        # 업로드한 파일 확인 테이블
        self.save_file_log = QTableWidget()
        self.save_file_log.setColumnCount(1)
        self.save_file_log.setHorizontalHeaderLabels(['Saved files'])
        self.save_file_log.horizontalHeader().setStretchLastSection(True) #테이블 마지막 열을 남늠 공간까지 자동으로 늘림
        self.save_file_log.setEditTriggers(QAbstractItemView.NoEditTriggers) #셀 수정 붏가

        # x축 부분 라벨과 콤보박스
        self.x_text = QLabel('x: ')
        self.x_text_cb = QComboBox()
        self.x_text_cb.addItems(['', '추가']) #x축 선택지에 들어갈 내용 작성 가장 처음에 빈 공란으로 두셔야 시작할 때 공백으로 뜸
        self.x_text_cb.adjustSize() #콤보박스 크기 내부 내용에 맞게 자동 조정

        # y축 부분 라벨과 콤보박스
        self.y_text = QLabel('y: ')
        self.y_text_cb = QComboBox()
        self.y_text_cb.addItems(['', '추가'])  # y축 선택지에 들어갈 내용 작성 가장 처음에 빈 공란으로 두셔야 시작할 때 공백으로 뜸
        self.y_text_cb.adjustSize()  # 콤보박스 크기 내부 내용에 맞게 자동 조정

        # 그래프 시작 버튼
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start)

        # 그래프 공간 임의 제작
        self.graph_space = QLabel()
        self.graph_space.setMaximumHeight(500) #공간을 주기위해 적은 것으로 제작시 제거해도 됨
        self.graph_space.setMinimumWidth(500) #공간을 주기위해 적은 것으로 제작시 제거해도 됨

    def upload(self):
        pass

    def start(self):
        pass

    def setup(self):
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

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addWidget(self.graph_space)

        self.setLayout(layout2)