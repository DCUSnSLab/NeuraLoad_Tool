from PyQt5.QtWidgets import QTableWidgetItem, QTabWidget, QWidget, QTableWidget
from PyQt5.QtCore import Qt

class WeightTable(QTableWidget):
    def __init__(self):
        super().__init__(3,3)
        self.elements = [None,None,None,None,None,None,None,None,None]

        self.wtables = []
        self.setMinimumHeight(200)
        cnt = 0
        for row in range(3):
            for col in range(3):
                val = QTableWidgetItem()
                val.setText(str(-1))
                val.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, val)
                self.elements[cnt] = val
                cnt += 1

        self.count = 0
        self.cellChanged.connect(lambda row, col: self.onCellChanged(row, col))

    def setElement(self, index, value):
        row, col = divmod(index, 3)
        item = self.item(row, col)
        if item:
            item.setText(value)

    def addWeightTable(self, wt):
        self.wtables.append(wt)

    def onCellChanged(self, row, col):
        index = row * 3 + col
        changed_val = self.item(row, col).text()
        for wt in self.wtables:
            wt.setElement(index, changed_val)

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
                self.data_update()