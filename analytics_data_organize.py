import chunk
import os.path
import struct
from queue import Queue

from PyQt5.QtWidgets import QWidget, QMainWindow, QDockWidget
from collections import defaultdict, Counter

from numpy.distutils.fcompiler import pg


class AnalyticsData(QWidget):
    def __init__(self, path, file_name, loc):
        super().__init__()
        self.struct_format = '<d9H16sBHHH'
        self.record_size = struct.calcsize(self.struct_format)

        # analytics_data에서 전달하는 값들
        self.path = path
        self.file_name = file_name
        if isinstance(loc, int):
            self.loc = [loc]
        else:
            self.loc = loc

        self.buffer = {}
        self.loc_counter = defaultdict(Counter)
        self.total_common = {}

        self.open_file()
        self.draw_graph()

    def open_file(self):
        for i in range(len(self.file_name)):
            file_path = os.path.join(self.path, self.file_name[i])
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.record_size):
                    unpacked = struct.unpack(self.struct_format, chunk)
                    self.data_select(unpacked)

            self.find_mode()

    def data_select(self, unpacked):
        weight = unpacked[1:10]

        if sum(weight) == 0 or all(weight[i] != 0 for i in self.loc):
            weight_total = sum(weight)
            data = [weight_total, unpacked[10], unpacked[12]]

            self.group_by_port(data)

    def group_by_port(self, data):
        weight = data[0]
        loc = data[1].decode('utf-8').rstrip('\x00')
        value = data[2]

        if loc not in self.buffer:
            self.buffer[loc] = Queue()

        self.buffer[loc].put((weight, value))

    def find_mode(self):
        data = defaultdict(lambda: defaultdict(list))

        for loc, q in self.buffer.items():
            while not q.empty():
                weight, value = q.get()
                data[loc][weight].append(value)

        for loc, weight_dict in data.items():
            self.total_common[loc] = {}
            for weight, values in weight_dict.items():
                counter = Counter(values)
                most_common_value = counter.most_common(1)[0][0]
                self.total_common[loc][weight] = most_common_value