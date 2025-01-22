import sys
from PyQt5.QtWidgets import *
import pyqtgraph as pg


class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()
        self.setupUI()
        self.Setup()

    def initUI(self):
        self.setWindowTitle('과적 그래프 확인')
        self.show()

    def setupUI(self):
        self.load_data = QPushButton('파일 업로드', self)
        self.load_data.clicked.connect(self.Load)
        self.load_data.setMinimumWidth(1400)

        self.graph_real = pg.PlotWidget()
        self.graph_real.setTitle("데이터 실제값")
        self.graph_real.setLabel("bottom", "weight")
        self.graph_real.setMinimumWidth(700)
        self.graph_real.setMinimumHeight(700)

        self.graph_change = pg.PlotWidget()
        self.graph_change.setTitle("데이터 변화량")
        self.graph_change.setLabel("bottom", "weight")
        self.graph_change.setMinimumWidth(700)
        self.graph_change.setMinimumHeight(700)

    def Load(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*);;yaml Files (*.yaml)", options=options)
        if files:
            for file in files:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    for line in lines:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key, value = parts[0].strip(), parts[1].strip()

                            # 데이터 처리 (예: value 추가 처리)
                            if key == "timestamp":
                                # timestamp일 경우 값에서 큰따옴표 제거
                                timestamp = value.strip('"')
                            elif key.startswith("Data_port"):
                                # Data_port 데이터 처리 (쉼표로 나눔)
                                data_port_values = value.split(',')
                            elif key == "load":
                                # load 데이터 처리
                                load_value = value
                            else:
                                continue

                            # 하나의 리스트에 병합
                            combined_data = [timestamp, key] + data_port_values + [load_value]
                            print(combined_data)
                except Exception as e:
                    print(f"Failed to process file {file}: {e}")

    def Setup(self):
        layout = QHBoxLayout()
        layout.addWidget(self.graph_real)
        layout.addWidget(self.graph_change)

        layout1 = QVBoxLayout()
        layout1.addWidget(self.load_data)
        layout1.addLayout(layout)

        self.setLayout(layout1)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = MyApp()
   sys.exit(app.exec_())