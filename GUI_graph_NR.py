from PyQt5.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np


class GraphWidget(QWidget):
    def __init__(self, title="Graph", parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Plot Widget 설정
        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend(offset=(10, 10))  # ✅ 범례 추가

        # ✅ ViewBox에 대한 직접 참조 가져오기
        self.viewbox = self.plot_widget.plotItem.getViewBox()

        # ✅ 자동 범위 조정 비활성화 (X, Y 모두)
        self.viewbox.disableAutoRange()

        # 값 표시용 라벨
        self.value_text = pg.TextItem(text="", anchor=(0, 0))
        self.value_text.setZValue(100)  # 다른 요소들 위에 표시
        self.plot_widget.addItem(self.value_text)

        # 십자선 추가
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        # 마우스 이벤트 연결
        self.plot_widget.scene().sigMouseMoved.connect(self.onMouseMoved)

        self.main_layout.addWidget(self.plot_widget)
        self.lines = dict()
        self.data_dict = {}  # 원본 데이터 저장

        # ✅ 미리 색상 목록 준비 (반복적으로 사용 가능)
        self.colors = [
            'r', 'g', 'b', 'c', 'm', 'y', 'w', 'k',
            '#FF7F0E', '#1F77B4', '#2CA02C', '#D62728'
        ]
        self.color_index = 0

    def onMouseMoved(self, pos):
        """마우스 이동 이벤트 핸들러"""
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        # 마우스 좌표를 데이터 좌표로 변환
        mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x = int(mousePoint.x())
        y = mousePoint.y()

        # 십자선 위치 업데이트
        self.vLine.setPos(x)
        self.hLine.setPos(y)

        # 데이터 값 표시
        if self.data_dict and 0 <= x < len(next(iter(self.data_dict.values()), [])):
            text = f""

            for label, data in self.data_dict.items():
                if 0 <= x < len(data):
                    text += f"{label}: {data[x]:.2f}\n"

            # 텍스트 업데이트 및 위치 설정
            self.value_text.setText(text)

            # ✅ 화면 경계 내에 텍스트 위치 설정
            view_range = self.viewbox.viewRange()
            text_x = max(view_range[0][0], min(x, view_range[0][1] - 100))
            text_y = view_range[1][0] + (view_range[1][1] - view_range[1][0]) * 0.6

            self.value_text.setPos(text_x, y)
            self.value_text.setVisible(True)

            # ✅ 마우스 이동 중에도 범위가 변경되지 않도록 범위 복원
            if self.current_range is not None:
                self.viewbox.setRange(xRange=self.current_range[0], yRange=self.current_range[1], padding=0)
        else:
            self.value_text.setVisible(False)

    def clear(self):
        self.plot_widget.clear()
        self.plot_widget.addLegend(offset=(10, 10))  # ✅ 범례 재추가

        # 십자선과 라벨 다시 추가
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        self.plot_widget.addItem(self.value_text)

        self.lines.clear()
        self.color_index = 0  # 색상 인덱스 초기화
        self.data_dict = {}  # 데이터 초기화
        self.current_range = None  # 범위 초기화

    def set_data(self, data_dict):
        """
        데이터를 받아서 그래프에 그림.
        :param data_dict: {label: [y1, y2, ...], ...}
        """
        self.clear()
        self.data_dict = data_dict

        # 데이터가 없으면 종료
        if not data_dict:
            return

        # 모든 데이터의 최대/최소값 계산
        x_max = max(len(data) for data in data_dict.values())
        x_min = 0

        all_values = []
        for data in data_dict.values():
            all_values.extend(data)

        if all_values:
            y_min = min(all_values)
            y_max = max(all_values)
        else:
            y_min, y_max = 0, 1

        # 약간의 여유 공간 추가
        y_range = y_max - y_min
        y_min -= y_range * 0.05
        y_max += y_range * 0.05

        for label, data in data_dict.items():
            x = list(range(len(data)))

            color = self.colors[self.color_index % len(self.colors)]
            pen = pg.mkPen(color=color, width=2)

            curve = self.plot_widget.plot(x, data, pen=pen, name=label)  # ✅ name으로 범례 표시
            self.lines[label] = curve
            self.color_index += 1

        # ✅ 범위 설정 및 저장
        self.viewbox.setRange(xRange=[x_min, x_max], yRange=[y_min, y_max], padding=0)
        self.current_range = ([x_min, x_max], [y_min, y_max])

        # ✅ 자동 범위 조정 비활성화
        self.viewbox.disableAutoRange()

    def set_title(self, title):
        self.plot_widget.setTitle(title)

    def set_axis_labels(self, xlabel="X Axis", ylabel="Y Axis"):
        self.plot_widget.setLabel('bottom', xlabel)
        self.plot_widget.setLabel('left', ylabel)

    # ✅ 수동으로 범위를 재설정하는 메서드 추가
    def reset_view(self):
        """그래프 보기를 데이터의 전체 범위로 재설정"""
        if self.current_range:
            self.viewbox.setRange(xRange=self.current_range[0], yRange=self.current_range[1], padding=0)

