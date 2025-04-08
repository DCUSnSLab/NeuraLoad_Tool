import os
import importlib.util
import random
import time
from multiprocessing import Queue
from AlgorithmInterface import AlgorithmBase

class Algorithm_multiprocess:
    def __init__(self, file_input):
        self.file_name_input = file_input
        self.databuf = Queue(maxsize=1000)

    def random_data(self):
        sensor_values = {
            'a': random.randint(300, 450),
            'b': random.randint(300, 450),
            'c': random.randint(300, 450),
            'd': random.randint(300, 450)
        }

        wrapped_data = {
            'sensor_values': sensor_values
        }

        self.databuf.put(wrapped_data)

    def run(self, file_name_input):
        folder = os.path.join(os.getcwd(), 'Algorithm')
        full_path = os.path.join(folder, file_name_input)

        file_name = os.path.splitext(os.path.basename(full_path))[0]
        spec = importlib.util.spec_from_file_location(file_name, full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, AlgorithmBase) and obj is not AlgorithmBase:
                instance = obj()
                while True:
                    self.random_data()
                    time.sleep(1)
                    value = self.databuf.get()
                    result = instance.execute(value)

                    print(result)
                    # result_queue.put(str(result))