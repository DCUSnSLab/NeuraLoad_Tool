import struct
import json
import os

def bin_to_json(bin_path, json_path):
    record_size = 52
    records = []

    if not os.path.exists(bin_path):
        print(f"BIN 파일 없음: {bin_path}")
        return

    with open(bin_path, 'rb') as f:
        while True:
            chunk = f.read(record_size)
            if len(chunk) < record_size:
                break

            timestamp_int = struct.unpack('<I', chunk[:4])[0]
            timestamp_str = str(timestamp_int)

            weights = struct.unpack('<9h', chunk[4:22])
            direction = chunk[22:23].decode('utf-8')
            name = chunk[23:39].split(b'\x00', 1)[0].decode('utf-8')
            values = struct.unpack('<fff', chunk[39:51])
            state = chunk[51:52].decode('utf-8')

            records.append({
                "timestamp": timestamp_str,
                "weights": list(weights),
                "direction": direction,
                "name": name,
                "value1": values[0],
                "value2": values[1],
                "value3": values[2],
                "state": state
            })

    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(records, json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    bin_to_json("./log/raw_data_2025-04-05.bin", "./log/raw_data_2025-04-05.json")
