from datetime import datetime
import random
import os
import re
import struct

class ChangeDataFormat:
    def __init__(self):
        self.path = r"\\203.250.32.43\SnSlab\자료실\데이터셋\화물 과적 적재 실험 데이터\분류된 백업 데이터\1st_experiment_data.yaml"
        self.save_path = r"\\203.250.32.43\SnSlab\자료실\데이터셋\화물 과적 적재 실험 데이터\데이터 형식 변경"

        self.struct_format = '<d 9H 16s B H H H'

        self.data_split()

    def data_split(self):
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i in range(0, len(lines) - 1, 2):
            line = lines[i+1].strip() + " " + lines[i].strip()

            timestamp_match = re.search(r'timestamp:\s*"(.+?)"', line)
            timestamp = timestamp_match.group(1) #형태: 2025-01-07 08:27:01.28

            port_match = re.search(r'Data_port_(\d+):\s*(.+?)\s*,\s*load:', line)
            if port_match:
                port_num = int(port_match.group(1))

                port_map = {
                    1: 'TopLeft',
                    2: 'TopRight',
                    3: 'BottomLeft',
                    4: 'BottomRight',
                }

                port = port_map.get(port_num)
                values_str = port_match.group(2)
                try:
                    data = int(values_str.split(',')[0])
                except:
                    continue

            load = re.search(r'load:\s*(\S+)', line)
            if load:
                load_value = load.group(1)

                if "_" in load_value:
                    loc, weight = load_value.split('_')
                    self.data_organise(timestamp, port, data, loc, weight)

    def data_organise(self, timestamp, port, data, loc, weight):
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
        timestamp_float = dt.timestamp()

        self.data_file_create(timestamp_float, loc, weight, port, data)

    def data_file_create(self, timestamp_float, loc, weight, port, data):
        value1 = random.randint(100, 500)
        value2 = random.randint(100, 500)

        weight_list = [0] * 9
        weight_list[int(loc)-1] = int(weight)

        direction = 0

        packed = struct.pack(
                self.struct_format,
                timestamp_float,
                *weight_list,
                port.encode('utf-8').ljust(16, b'\x00'),
                direction,
                int(data),
                value1,
                value2
            )

        filename = os.path.basename(self.path)
        base_name = os.path.splitext(filename)[0]
        new_filename = f"format_{base_name}.bin"
        new_path = os.path.join(self.save_path, new_filename)

        os.makedirs(self.save_path, exist_ok=True)

        with open(new_path, 'ab') as f:
            f.write(packed)


if __name__ == "__main__":
    ChangeDataFormat()
    print('저장 완료')