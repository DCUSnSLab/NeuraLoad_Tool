from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt

class ProgressWidget(QWidget):
    def __init__(self, title="Progress", parent=None):
        super().__init__(parent)

        self.total = 100
        self.current = 0

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        self.inner_layout = QVBoxLayout()
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(2)

        self.label = QLabel(title)
        self.statusLabel = QLabel('Ready..')
        self.label.setAlignment(Qt.AlignLeft)  # 필요하면 중앙정렬로 바꿔도 됨

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total)
        self.progress_bar.setValue(self.current)

        # 여기 추가된 부분!
        self.progress_bar.setFormat("%p%")  # 진행률 %로 표시
        self.progress_bar.setTextVisible(True)

        self.inner_layout.addWidget(self.label)
        self.inner_layout.addWidget(self.statusLabel)
        self.inner_layout.addWidget(self.progress_bar)

        self.main_layout.addLayout(self.inner_layout)
        self.main_layout.addStretch()

    def set_total(self, total):
        self.total = total
        self.progress_bar.setMaximum(total)

    def set_value(self, value):
        self.current = value
        self.progress_bar.setValue(value)

    def increment(self, step=1):
        self.current += step
        if self.current > self.total:
            self.current = self.total
        self.progress_bar.setValue(self.current)

    def reset(self):
        self.current = 0
        self.progress_bar.setValue(0)

    def set_title(self, title):
        self.label.setText(title)

    def set_status(self, status):
        self.statusLabel.setText(status)
