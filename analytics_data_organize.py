import chunk
import os.path
import struct
from queue import Queue

from PyQt5.QtWidgets import QWidget, QMainWindow, QDockWidget
from collections import defaultdict, Counter

from analytics_graph import AnalyticsGraph
from datainfo import SensorBinaryFileHandler


class AnalyticsDataOrganize(QWidget):
    def __init__(self, path, x, y, file_name, loc):
        super().__init__()
        self.path = path
        self.x = x
        self.y = y
        self.file_name = file_name
        if isinstance(loc, int):
            self.loc = [loc]
        else:
            self.loc = loc

        self.buffer = {}
        self.loc_counter = defaultdict(Counter)
        self.total_common = {}

        self.open_file()


    def open_file(self):
        count = 0
        for i in range(len(self.file_name)):
            self.buffer.clear()
            load_data = SensorBinaryFileHandler(self.file_name[i]).load_frames()
            count += 1
            self.data_select(load_data, count)

            self.find_mode()

    def data_select(self, load_data, count):
        for data in load_data:
            for sensor in data.sensors:
                weight = data.experiment.weights
                location = sensor.location.name
                distance = sensor.distance

                if self.x == 0 and self.y == 0:
                    # distance_change = previous_distance - distance
                    pass


                if sum(weight) == 0 or all(weight[i] != 0 for i in self.loc):
                    weight_total = sum(weight)
                    data_list = [weight_total, location, distance]

                    self.group_by_port(data_list, count)

    def group_by_port(self, data_list, count):
        weight = data_list[0]
        loc = data_list[1]
        value = data_list[2]

        buffer_name = loc + "_" + str(count)

        if buffer_name not in self.buffer:
            self.buffer[buffer_name] = Queue()

        self.buffer[buffer_name].put((weight, value))

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

        AnalyticsGraph(self.total_common)