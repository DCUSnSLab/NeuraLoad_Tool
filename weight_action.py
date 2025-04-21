from PyQt5.QtWidgets import QTableWidgetItem, QTabWidget, QWidget, QTableWidget, QLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class WeightTable(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self.elements = [None,None,None,None,None,None,None,None,None]

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
        changed_val = self.boxwidget.item(row, col).text()
        for wt in self.wtables:
            wt.setElement(index, changed_val)