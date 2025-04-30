from PyQt5.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
from pyqtgraph import PlotWidget

class BarGraphWidget(QWidget):
    def __init__(self, title="Error Metrics", parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.plot_widget = PlotWidget(title=title)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('w')
        self.layout.addWidget(self.plot_widget)

        # 색깔 리스트 준비
        self.colors = [
            'red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow'
        ]

    def set_data(self, makedData: dict, mode: str = 'mae'):
        """
        mode: 'mae', 'mse', 'rmse', 'error_rate'
        """
        self.plot_widget.clear()

        if "Actual Weights" not in makedData:
            return

        actual = makedData["Actual Weights"]
        avg_actual = sum(actual) / len(actual) if actual else 1

        x = []
        heights = []
        labels = []

        for i, (key, predicted) in enumerate(makedData.items()):
            if key == "Actual Weights":
                continue
            if len(predicted) != len(actual):
                continue

            # 에러 계산
            if mode == 'mae':
                error = sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)
            elif mode == 'mse':
                error = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)
            elif mode == 'rmse':
                mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)
                error = mse ** 0.5
            elif mode == 'error_rate':
                mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)
                error = (mae / avg_actual) * 100
            else:
                error = 0

            x.append(i)
            heights.append(error)
            labels.append(key)

        # 각각 다른 색으로 Bar 그리기
        for i in range(len(x)):
            color = self.colors[i % len(self.colors)]  # 색 순환
            bar = pg.BarGraphItem(x=[x[i]], height=[heights[i]], width=0.6, brush=color)
            self.plot_widget.addItem(bar)

            # 막대 위에 숫자 표시
            text = pg.TextItem(text=f"{heights[i]:.2f}", anchor=(0.5, -0.5))
            text.setPos(x[i], heights[i])
            self.plot_widget.addItem(text)

        # X축 라벨 설정
        ax = self.plot_widget.getAxis('bottom')
        ax.setTicks([list(zip(x, labels))])

        ylabel = mode.upper()
        if mode == 'error_rate':
            ylabel = 'Error Rate (%)'

        self.plot_widget.setLabel('left', ylabel)
        self.plot_widget.setLabel('bottom', 'Algorithm')
