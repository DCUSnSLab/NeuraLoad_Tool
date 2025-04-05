import struct
import ast

def txt_to_bin(txt_path, bin_path):
    with open(txt_path, 'r') as txt_file, open(bin_path, 'wb') as bin_file:
        for line in txt_file:
            parts = line.strip().split('\t')
            if len(parts) != 7:
                continue  # Skip malformed lines

            timestamp_str = parts[0].replace('_', '')
            timestamp_int = int(timestamp_str)

            weights = ast.literal_eval(parts[1])  # safely parse string list
            if len(weights) != 9:
                continue

            direction = parts[2].encode('utf-8')
            name = parts[3].encode('utf-8')[:16] + b'\x00' * (16 - len(parts[3].encode('utf-8')))
            value1 = float(parts[4])
            value2 = float(parts[5])
            value3 = float(parts[6])
            state = parts[6 + 1].encode('utf-8') if len(parts) > 7 else b't'

            packed = struct.pack(
                '<I9h1s16sfff1s',
                timestamp_int,
                *weights,
                direction,
                name,
                value1,
                value2,
                value3,
                state
            )

            bin_file.write(packed)

if __name__ == "__main__":
    txt_to_bin("../input.txt", "../output.bin")
