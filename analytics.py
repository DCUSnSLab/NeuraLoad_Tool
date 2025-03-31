from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit

class Analytics(QWidget):
    def __init__(self):
        super().__init__()
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.text_log)
        self.setLayout(layout)

    def update_data(self, port, data):
        pass
