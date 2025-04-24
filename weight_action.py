from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QTableWidget, QVBoxLayout, QLabel, QCheckBox, QPushButton, QGroupBox
from PyQt5.QtCore import Qt

from Algorithm.algorithmtype import ALGORITHM_TYPE


class WeightTable(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self.elements = [None,None,None,None,None,None,None,None,None]
        self.weights = [0] * 9

        #set Table
        self.boxwidget = QTableWidget(3,3)

        self.wtables = []
        self.boxwidget.setMinimumHeight(200)
        cnt = 0
        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem()
                val.setText(str(0))
                val.setTextAlignment(Qt.AlignCenter)
                self.boxwidget.setItem(row, col, val)
                self.elements[cnt] = val
                cnt += 1

        self.count = 0
        self.boxwidget.cellChanged.connect(lambda row, col: self.onCellChanged(row, col))

        #set Title
        self.title_label = QLabel('Weight Table')

        self.addWidget(self.title_label)
        self.addWidget(self.boxwidget)


    def setElement(self, index, value):
        row, col = divmod(index, 3)
        item = self.boxwidget.item(row, col)
        if item:
            item.setText(value)

    def addWeightTable(self, wt):
        self.wtables.append(wt)

    def onCellChanged(self, row, col):
        index = row * 3 + col
        item = self.boxwidget.item(row, col)
        if item:
            try:
                val = int(item.text())
            except ValueError:
                val = 0
                item.setText("0")
            self.weights[index] = val  # weights 업데이트
            for wt in self.wtables:
                wt.setElement(index, str(val))
            print(self.weights)

    def table_clear(self):
        cnt = 0
        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem()
                val.setText(str(0))
                val.setTextAlignment(Qt.AlignCenter)
                self.boxwidget.setItem(row, col, val)
                self.elements[cnt] = val
                self.weights[cnt] = 0
                cnt += 1

    def getWeights(self):
        return self.weights

class AlgorithmRunBox(QVBoxLayout):
    """
    알고리즘을 실행하기 위한 버튼과 체크 박스 UI
    실시간 알고리즘 테스트와 리시뮬레이션 기능이 동일한 UI를 가지기때문에 만듦
    """
    def __init__(self):
        super().__init__()
        self.files = dict()  # Algorithm File List
        self.algorithm_checkbox = []
        self.groupbox = None

        self.setAlgoLayout()

    def setAlgoLayout(self):
        self.algorithm_list = QWidget()
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)

        self.start_btn = QPushButton('Run the selected algorithm')
        self.all_btn = QPushButton('Run all')
        self.stop_btn = QPushButton('Stop and Reset')
        self.stop_btn.setEnabled(False)  # 알고리즘 프로세스가 시작해야 활성화됨

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)
        self.groupbox = QGroupBox('Currently available algorithms')
        self.groupbox.setLayout(layout)

        # Button
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.all_btn)
        btn_layout.addWidget(self.stop_btn)

        self.addWidget(self.groupbox)
        self.addLayout(btn_layout)

    def loadAlgorithmFileList(self):
        for algo_name in ALGORITHM_TYPE.list_all():
            self.files[algo_name.name] = algo_name
            checkbox = QCheckBox(algo_name.name)
            self.algorithm_checkbox.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)

    def getFileandCbx(self):
        return self.files, self.algorithm_checkbox