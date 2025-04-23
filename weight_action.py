from PyQt5.QtWidgets import QTableWidgetItem, QTabWidget, QWidget, QTableWidget, QLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

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