import sys
import os
import struct
import json
import ast
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QComboBox, QHBoxLayout
)


class FileConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TXT-BIN-JSON 변환기")
        self.setGeometry(300, 300, 420, 200)

        layout = QVBoxLayout()

        # 입력 형식 콤보박스
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("입력 형식:"))
        self.input_combo = QComboBox()
        self.input_combo.addItems(["txt", "bin", "json"])
        input_layout.addWidget(self.input_combo)
        layout.addLayout(input_layout)

        # 출력 형식 콤보박스
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("출력 형식:"))
        self.output_combo = QComboBox()
        self.output_combo.addItems(["txt", "bin", "json"])
        output_layout.addWidget(self.output_combo)
        layout.addLayout(output_layout)

        # 변환 버튼
        self.convert_button = QPushButton("변환 실행")
        self.convert_button.clicked.connect(self.convert_file)
        layout.addWidget(self.convert_button)

        self.setLayout(layout)

    def convert_file(self):
        input_type = self.input_combo.currentText()
        output_type = self.output_combo.currentText()

        if input_type == output_type:
            QMessageBox.warning(self, "경고", "입력 형식과 출력 형식이 동일합니다.")
            return

        try:
            if input_type == "txt" and output_type == "bin":
                self.txt_to_bin()
            elif input_type == "bin" and output_type == "json":
                self.bin_to_json()
            elif input_type == "json" and output_type == "txt":
                self.json_to_txt()
            elif input_type == "bin" and output_type == "txt":
                self.bin_to_txt()
            elif input_type == "json" and output_type == "bin":
                self.json_to_bin()
            elif input_type == "txt" and output_type == "json":
                self.txt_to_json()
            else:
                QMessageBox.warning(self, "지원되지 않는 조합", f"{input_type} → {output_type} 변환은 아직 지원하지 않습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"변환 실패: {e}")

    def txt_to_bin(self):
        txt_path, _ = QFileDialog.getOpenFileName(self, "TXT 파일 선택", "", "Text Files (*.txt)")
        if not txt_path:
            return
        bin_path, _ = QFileDialog.getSaveFileName(self, "저장할 BIN 파일", "", "Binary Files (*.bin)")
        if not bin_path:
            return

        with open(txt_path, 'r') as txt_file, open(bin_path, 'wb') as bin_file:
            for line in txt_file:
                parts = line.strip().split('\t')
                if len(parts) < 7:
                    continue
                timestamp_str = parts[0].replace('_', '')
                timestamp_int = int(timestamp_str)
                weights = ast.literal_eval(parts[1])
                if len(weights) != 9:
                    continue
                direction = parts[2].encode('utf-8')
                name = parts[3].encode('utf-8')[:16].ljust(16, b'\x00')
                value1 = float(parts[4])
                value2 = float(parts[5])
                value3 = float(parts[6])
                state = parts[7].encode('utf-8') if len(parts) > 7 else b't'

                packed = struct.pack(
                    '<I9h1s16sfff1s',
                    timestamp_int,
                    *weights,
                    direction,
                    name,
                    value1,
                    value2,
                    value3,
                    state
                )
                bin_file.write(packed)

        QMessageBox.information(self, "완료", "TXT → BIN 변환 완료!")

    def bin_to_json(self):
        bin_path, _ = QFileDialog.getOpenFileName(self, "BIN 파일 선택", "", "Binary Files (*.bin)")
        if not bin_path:
            return
        json_path, _ = QFileDialog.getSaveFileName(self, "저장할 JSON 파일", "", "JSON Files (*.json)")
        if not json_path:
            return

        record_size = 52
        records = []
        with open(bin_path, 'rb') as f:
            while True:
                chunk = f.read(record_size)
                if len(chunk) < record_size:
                    break

                timestamp_int = struct.unpack('<I', chunk[:4])[0]
                timestamp_str = str(timestamp_int)
                weights = struct.unpack('<9h', chunk[4:22])
                direction = chunk[22:23].decode('utf-8')
                name = chunk[23:39].split(b'\x00', 1)[0].decode('utf-8')
                values = struct.unpack('<fff', chunk[39:51])
                state = chunk[51:52].decode('utf-8')

                records.append({
                    "timestamp": timestamp_str,
                    "weights": list(weights),
                    "direction": direction,
                    "name": name,
                    "value1": values[0],
                    "value2": values[1],
                    "value3": values[2],
                    "state": state
                })

        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(records, json_file, indent=4, ensure_ascii=False)

        QMessageBox.information(self, "완료", "BIN → JSON 변환 완료!")

    def json_to_txt(self):
        json_path, _ = QFileDialog.getOpenFileName(self, "JSON 파일 선택", "", "JSON Files (*.json)")
        if not json_path:
            return
        txt_path, _ = QFileDialog.getSaveFileName(self, "저장할 TXT 파일", "", "Text Files (*.txt)")
        if not txt_path:
            return

        with open(json_path, 'r', encoding='utf-8') as json_file, open(txt_path, 'w') as txt_file:
            data = json.load(json_file)
            for item in data:
                line = f"{item['timestamp']}\t{item['weights']}\t{item['direction']}\t{item['name']}\t{item['value1']}\t{item['value2']}\t{item['value3']}\t{item['state']}\n"
                txt_file.write(line)

        QMessageBox.information(self, "완료", "JSON → TXT 변환 완료!")

    def bin_to_txt(self):
        bin_path, _ = QFileDialog.getOpenFileName(self, "BIN 파일 선택", "", "Binary Files (*.bin)")
        if not bin_path:
            return
        txt_path, _ = QFileDialog.getSaveFileName(self, "저장할 TXT 파일", "", "Text Files (*.txt)")
        if not txt_path:
            return

        record_size = 52
        with open(bin_path, 'rb') as f, open(txt_path, 'w') as txt_file:
            while True:
                chunk = f.read(record_size)
                if len(chunk) < record_size:
                    break

                timestamp = struct.unpack('<I', chunk[:4])[0]
                weights = struct.unpack('<9h', chunk[4:22])
                direction = chunk[22:23].decode('utf-8')
                name = chunk[23:39].split(b'\x00', 1)[0].decode('utf-8')
                values = struct.unpack('<fff', chunk[39:51])
                state = chunk[51:52].decode('utf-8')

                line = f"{timestamp}\t{list(weights)}\t{direction}\t{name}\t{values[0]}\t{values[1]}\t{values[2]}\t{state}\n"
                txt_file.write(line)

        QMessageBox.information(self, "완료", "BIN → TXT 변환 완료!")

    def json_to_bin(self):
        json_path, _ = QFileDialog.getOpenFileName(self, "JSON 파일 선택", "", "JSON Files (*.json)")
        if not json_path:
            return
        bin_path, _ = QFileDialog.getSaveFileName(self, "저장할 BIN 파일", "", "Binary Files (*.bin)")
        if not bin_path:
            return

        with open(json_path, 'r', encoding='utf-8') as json_file, open(bin_path, 'wb') as bin_file:
            data = json.load(json_file)
            for item in data:
                timestamp_int = int(item['timestamp'])
                weights = item['weights']
                direction = item['direction'].encode('utf-8')
                name = item['name'].encode('utf-8')[:16].ljust(16, b'\x00')
                value1 = float(item['value1'])
                value2 = float(item['value2'])
                value3 = float(item['value3'])
                state = item['state'].encode('utf-8')

                packed = struct.pack(
                    '<I9h1s16sfff1s',
                    timestamp_int,
                    *weights,
                    direction,
                    name,
                    value1,
                    value2,
                    value3,
                    state
                )
                bin_file.write(packed)

        QMessageBox.information(self, "완료", "JSON → BIN 변환 완료!")

    def txt_to_json(self):
        txt_path, _ = QFileDialog.getOpenFileName(self, "TXT 파일 선택", "", "Text Files (*.txt)")
        if not txt_path:
            return
        json_path, _ = QFileDialog.getSaveFileName(self, "저장할 JSON 파일", "", "JSON Files (*.json)")
        if not json_path:
            return

        records = []
        with open(txt_path, 'r') as txt_file:
            for line in txt_file:
                parts = line.strip().split('\t')
                if len(parts) < 7:
                    continue
                timestamp = parts[0].replace('_', '')
                weights = ast.literal_eval(parts[1])
                direction = parts[2]
                name = parts[3]
                value1 = float(parts[4])
                value2 = float(parts[5])
                value3 = float(parts[6])
                state = parts[7] if len(parts) > 7 else 't'

                records.append({
                    "timestamp": timestamp,
                    "weights": weights,
                    "direction": direction,
                    "name": name,
                    "value1": value1,
                    "value2": value2,
                    "value3": value3,
                    "state": state
                })

        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(records, json_file, indent=4, ensure_ascii=False)

        QMessageBox.information(self, "완료", "TXT → JSON 변환 완료!")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    converter = FileConverter()
    converter.show()
    sys.exit(app.exec_())
