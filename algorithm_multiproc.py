import os
from multiprocessing import Process, Manager
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from AlgorithmLauncher import launch_algorithm


class AlgorithmMultiProc(QWidget):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager

        self.files = dict() #Algorithm File List
        self.algorithm_checkbox = []
        self.outputLabels = []

        self.loadAlgorithmFromFile()
        self.initUI()

    def initUI(self):
        self.algorithm_list = QWidget(self)
        self.checkbox_layout = QVBoxLayout()
        self.algorithm_list.setLayout(self.checkbox_layout)
        for cbx in self.algorithm_checkbox:
            self.checkbox_layout.addWidget(cbx)

        self.start_btn = QPushButton('Run the selected algorithm', self)
        self.start_btn.clicked.connect(self.run)

        # self.reset_btn = QPushButton('Reset', self)
        # self.reset_btn.clicked.connect(self.reset)

        self.all_btn = QPushButton('Run all', self)
        self.all_btn.clicked.connect(self.run_all)

        layout = QVBoxLayout()
        layout.addWidget(self.algorithm_list)

        groupbox = QGroupBox('Currently available algorithms')
        groupbox.setLayout(layout)

        self.weight_layout = QVBoxLayout()
        #weight_layout1.addWidget(self.actual_weight_text)

        self.weight_layout.addStretch()
        self.weight_layout.setSpacing(10)
        #
        # weight_layout2 = QHBoxLayout()
        # weight_layout2.addWidget(self.actual_location_text)
        # weight_layout2.addWidget(self.actual_location_output)
        # weight_layout2.addStretch()
        # weight_layout2.setSpacing(10)
        #
        layout = QVBoxLayout()
        layout.addLayout(self.weight_layout)
        # layout.addLayout(weight_layout2)
        # layout.addWidget(self.weight_table)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        # btn_layout.addWidget(self.reset_btn)
        layout1 = QVBoxLayout()
        layout1.addWidget(groupbox)
        layout1.addLayout(btn_layout)
        layout1.addWidget(self.all_btn)

        layout2 = QHBoxLayout()
        layout2.addLayout(layout1)
        layout2.addLayout(layout)

        self.setLayout(layout2)

    def setOutputLabels(self):
        self.clear_layout(self.weight_layout)

        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                layout = QHBoxLayout()
                layout.addWidget(QLabel(cbx.text()))
                dataLabel = QLabel('-')
                layout.addWidget(dataLabel)
                self.weight_layout.addLayout(layout)
                self.outputLabels.append(dataLabel)


    def clear_layout(self, layout):
        while layout.count():
            print('delete layout - ',layout)
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            # layout 안에 또 다른 layout이 있을 수 있으므로 재귀적으로 처리
            elif item.layout() is not None:
                self.clear_layout(item.layout())
    def loadAlgorithmFromFile(self):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        py_files = [f for f in os.listdir(folder) if f.endswith('.py')]

        for file_name in py_files:
            full_path = os.path.join(folder, file_name)
            self.files[file_name] = full_path
            checkbox = QCheckBox(file_name)
            self.algorithm_checkbox.append(checkbox)

    def run(self):
        self.runAlgorithm()

    def run_all(self):
        for cbx in self.algorithm_checkbox:
            cbx.setChecked(True)
        self.runAlgorithm()

    def runAlgorithm(self):
        self.algo_processes = {}
        parent_manager = Manager()

        for cbx in self.algorithm_checkbox:
            if cbx.isChecked():
                algo_file = cbx.text()
                if algo_file in self.files:
                    # 부모에서 공유 큐를 생성
                    shared_buffer = parent_manager.Queue()
                    # 등록: 공유 큐를 serial_manager에 등록
                    self.serial_manager.add_buffer(shared_buffer)

                    # Process 생성: launch_algorithm 함수에 file_path와 shared_buffer 전달
                    pr = Process(
                        name=algo_file,
                        target=launch_algorithm,
                        args=(self.files[algo_file], shared_buffer)
                    )
                    pr.start()
                    self.algo_processes[algo_file] = (pr, shared_buffer)

        # 5초 후에 cleanup 함수를 호출 (각 프로세스 join 후 공유 큐 제거)
        QTimer.singleShot(5000, self.cleanupAlgoBuffers)

    def cleanupAlgoBuffers(self):
        for algo_file, (process, shared_buffer) in self.algo_processes.items():
            process.join()  # 프로세스 종료 대기
            # 등록했던 공유 큐 제거
            self.serial_manager.remove_buffer(shared_buffer)
        self.algo_processes.clear()