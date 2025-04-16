from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class WeightTable(QWidget):
    def __init__(self):
        super().__init__()
        self.weight_a = [-1] * 9
        self.count = 0

        self.ui()

    def broadcast_weight(self):
        for sub in self.subscribers:
            # 각 subscriber가 set_weight 메소드를 가지고 있는지 확인
            if hasattr(sub, 'set_weight'):
                sub.set_weight(self.weight_a)

    def ui(self):
        self.weight_table = QTableWidget(3, 3)
        self.weight_table.installEventFilter(self)
        self.weight_table.cellChanged.connect(self.onCellChanged)
        self.weight_table.setMinimumHeight(200)

        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem(str(self.weight_a[self.count]))
                val.setTextAlignment(Qt.AlignCenter)
                self.weight_table.setItem(row, col, val)
                self.count += 1

        self.weight_btn_p = QPushButton('+', self)
        self.weight_btn_p.clicked.connect(lambda: self.weight_update(True))

        self.weight_btn_m = QPushButton('-', self)
        self.weight_btn_m.clicked.connect(lambda: self.weight_update(False))

        layout_btn = QHBoxLayout()
        layout_btn.addWidget(self.weight_btn_p)
        layout_btn.addWidget(self.weight_btn_m)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.weight_table)
        self.layout.addLayout(layout_btn)

    def onCellChanged(self, row, col):
        try:
            item = self.weight_table.item(row, col)
            if item is None:
                return

            new_value = item.text().strip()
            index = row * 3 + col

            if 0 <= index < len(self.weight_a):
                try:
                    self.weight_a[index] = int(new_value)
                    self.broadcast_weight()
                except ValueError:
                    prev_value = self.weight_a[index]
                    item.setText(str(prev_value))
            else:
                prev_value = -1
                item.setText(str(prev_value))

        except Exception as e:
            print(f"onCellChanged 오류: {e}")
            # 로그 출력 객체가 있는지 확인
            if hasattr(self, 'log_output'):
                self.log_output.append(f"onCellChanged 오류: {e}")

    def weight_update(self, TF):
        selected_items = self.weight_table.selectedItems()
        if selected_items:
            for val in selected_items:
                text = val.text().strip()
                current_value = int(text)

                row = val.row()
                col = val.column()

                index = row * 3 + col

                if TF:
                    if self.weight_a[index] == -1:
                        self.weight_a[index] = (current_value + 21)
                    else:
                        self.weight_a[index] = (current_value + 20)
                else:
                    if 0 <= index < len(self.weight_a):
                        if current_value < 20:
                            self.weight_a[index] = 0
                        else:
                            self.weight_a[index] = current_value - 20
                val.setText(str(self.weight_a[index]))

    def get_table(self):
        return self.layout