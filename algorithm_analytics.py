from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class AlgorithmAnalytics(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        label = QLabel("알고리즘 분석 기능\n추가 예정")
        layout.addWidget(label)
        self.setLayout(layout)