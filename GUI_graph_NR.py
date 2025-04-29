from PyQt5.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg

class GraphWidget(QWidget):
    def __init__(self, title="Graph", parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Plot Widget 설정
        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend(offset=(10, 10))  # ✅ 범례 추가

        self.main_layout.addWidget(self.plot_widget)
        self.lines = dict()

        # ✅ 미리 색상 목록 준비 (반복적으로 사용 가능)
        self.colors = [
            'r', 'g', 'b', 'c', 'm', 'y', 'w', 'k',
            '#FF7F0E', '#1F77B4', '#2CA02C', '#D62728'
        ]
        self.color_index = 0

    def clear(self):
        self.plot_widget.clear()
        self.plot_widget.addLegend(offset=(10, 10))  # ✅ 범례 재추가
        self.lines.clear()
        self.color_index = 0  # 색상 인덱스 초기화

    def set_data(self, data_dict):
        """
        데이터를 받아서 그래프에 그림.
        :param data_dict: {label: [y1, y2, ...], ...}
        """
        self.clear()

        for label, data in data_dict.items():
            x = list(range(len(data)))

            color = self.colors[self.color_index % len(self.colors)]
            pen = pg.mkPen(color=color, width=2)

            curve = self.plot_widget.plot(x, data, pen=pen, name=label)  # ✅ name으로 범례 표시
            self.lines[label] = curve
            self.color_index += 1

    def set_title(self, title):
        self.plot_widget.setTitle(title)

    def set_axis_labels(self, xlabel="X Axis", ylabel="Y Axis"):
        self.plot_widget.setLabel('bottom', xlabel)
        self.plot_widget.setLabel('left', ylabel)
