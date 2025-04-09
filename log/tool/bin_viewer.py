import struct
import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QPushButton, QFileDialog, QMessageBox
)

def read_bin_file(file_path):
    record_size = 52
    records = []

    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return []

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(record_size)
            if len(chunk) < record_size:
                break

            timestamp_int = struct.unpack('<I', chunk[:4])[0]
            weights = struct.unpack('<9h', chunk[4:22])
            direction = chunk[22:23].decode('utf-8')
            name = chunk[23:39].split(b'\x00', 1)[0].decode('utf-8')
            values = struct.unpack('<fff', chunk[39:51])
            state_flag = chunk[51:52].decode('utf-8')

            record = [timestamp_int, name, list(weights), direction] + list(values) + [state_flag]
            records.append(record)
    return records

class BinViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIN 파일 뷰어")
        self.resize(1000, 600)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 파일 열기 버튼
        self.open_button = QPushButton("BIN 파일 열기")
        self.open_button.clicked.connect(self.open_file_dialog)
        self.layout.addWidget(self.open_button)

        # 테이블 위젯
        self.table = QTableWidget()
        self.layout.addWidget(self.table)

    def open_file_dialog(self):
        # ./log 디렉토리를 기본 경로로 설정
        base_dir = os.path.abspath("./log")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "BIN 파일 선택",
            base_dir,
            "BIN 파일 (*.bin);;모든 파일 (*)"
        )

        if file_path:
            records = read_bin_file(file_path)
            if not records:
                QMessageBox.warning(self, "읽기 실패", "유효한 데이터를 찾을 수 없습니다.")
                return
            self.populate_table(records)

    def populate_table(self, records):
        headers = ["Timestamp", "Name", "Weights [W1~W9]", "Dir", "Val1", "Val2", "Val3", "State"]
        self.table.clear()
        self.table.setRowCount(len(records))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        for row_idx, record in enumerate(records):
            for col_idx, value in enumerate(record):
                display_value = str(value) if isinstance(value, list) else str(value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(display_value))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = BinViewer()
    viewer.show()
    sys.exit(app.exec_())