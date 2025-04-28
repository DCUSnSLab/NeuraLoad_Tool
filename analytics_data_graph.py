import chunk
import os.path
import struct

from PyQt5.QtWidgets import QWidget
from collections import defaultdict, Counter

class AnalyticsDataGraph(QWidget):
    def __init__(self, path, x, y, file_name, loc):
        super().__init__()
        self.struct_format = '<d9H16sBHHH'
        self.record_size = struct.calcsize(self.struct_format)

        # analytics_data에서 전달하는 값들
        self.path = path
        self.x = x
        self.y = y
        self.file_name = file_name
        if isinstance(loc, int):
            self.loc = [loc]
        else:
            self.loc = loc

        self.port_counter = defaultdict(Counter)

        self.open_file()
        self.find_common()

    # def open_file(self):
    #     for i in range(len(self.file_name)):
    #         file_data = SensorBinaryFileHandler(self.file_name[i]).load_frames()
    #         print(file_data)

    def open_file(self):
        for i in range(len(self.file_name)):
            file_path = os.path.join(self.path, self.file_name[i])
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.record_size):
                    unpacked = struct.unpack(self.struct_format, chunk)
                    self.data_select(unpacked)

    def data_select(self, unpacked):
        weight = unpacked[1:10]

        if sum(unpacked[1:10]) == 0:
            weight_total = 0

        elif all(weight[i] != 0 for i in self.loc):
            weight_total = sum(unpacked[1:10])

        data = [weight_total, unpacked[10], unpacked[13]]
        self.group_by_port(data)


    def group_by_port(self, data):
        loc = data[0].decode('utf-8').rstrip('\x00')
        value = data[1]
        self.port_counter[loc][value] += 1

    def find_common(self):
        for loc, value in self.port_counter.items():
            if value:
                most_common = value.most_common(1)[0][0] #y축