import os
from queue import Queue
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
import sys
import random
import datetime
from threading import Thread, Lock
import time


RAW_DATA_TEST_REPLAY = True # False 기존, True 임시값 전송

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "wch", "Serial"]):
            return port.device
    return None

def get_arduino_ports(DEBUG_MODE=False):
    if RAW_DATA_TEST_REPLAY:
        return [f"VCOM{i+1}" for i in range(4)]

    ports = serial.tools.list_ports.comports()
    ports = [
        port.device for port in ports
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "Serial", "wch"])
    ]

    if DEBUG_MODE:
        remainNumofPort = 4 - len(ports)
        if len(ports) != 0 and remainNumofPort > 0:
            for i in range(remainNumofPort):
                ports.append('VCOM'+str(i+1))
        print('Port, ', ports)
    return ports

class SerialThread(QThread):
    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.port = port or find_arduino_port()
        self.baudrate = baudrate
        self.is_running = True
        self.is_paused = False

        self.databuf = Queue(maxsize=1000)
        self.weight_a = [0] * 9

    def run(self):
        if RAW_DATA_TEST_REPLAY:
            self._run_dummy()
            return

        if not self.port:
            print("아두이노 포트를 찾을 수 없습니다.")
            return
        self.ser = serial.Serial(self.port, self.baudrate, timeout=1)

        while self.is_running:
            if not self.is_paused and self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]
                if data:
                    parts = data.split(',')
                    if len(parts) < 3:
                        continue
                    main_part = parts[0].strip()
                    sub_part1 = parts[1].strip()
                    sub_part2 = parts[2].strip()

                    if not main_part.isdigit():
                        continue
                    value = int(main_part)

                    self.databuf.put((timestamp, value, sub_part1, sub_part2))
            self.msleep(1)

    def _run_dummy(self):
        try:
            pidxGap = int(''.join(filter(str.isdigit, self.port))) - 1
        except ValueError:
            pidxGap = 0
        while self.is_running:
            timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]
            value = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part1 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part2 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            self.databuf.put((timestamp, value, sub_part1, sub_part2))
            self.msleep(100)

    def pause(self):
        self.is_paused = True

    def resume(self):
        if not RAW_DATA_TEST_REPLAY and hasattr(self, 'ser'):
            self.ser.flushInput()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()

class SerialThreadVirtual(SerialThread):
    def __init__(self, port, systemPorts):
        super().__init__(port)
        self.systemPorts = systemPorts

    def run(self):
        if not self.port:
            print("아두이노 포트를 찾을 수 없습니다.")
            return

        pidxGap = self.systemPorts.index(self.port)
        while self.is_running:
            # timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]

            # 현재 시간에 0~120ms 범위의 랜덤 오프셋 추가
            base_time = datetime.datetime.now()
            offset_ms = random.randint(0, 120)
            timestamp_dt = base_time + datetime.timedelta(milliseconds=offset_ms)
            # 타임스탬프 포맷: "HH_MM_SS_mmm"
            timestamp = timestamp_dt.strftime("%H_%M_%S_%f")[:-3]

            value = random.randint(400+(pidxGap*10), 450+(pidxGap*10))
            sub_part1 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part2 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            self.databuf.put((timestamp, value, sub_part1, sub_part2))
            self.msleep(100)


class SerialManager:
    """
    디버그 모드 여부에 따라 각 포트를 처리하는 스레드를 생성하고,
    각 스레드에서 발생한 데이터를 중앙에서 모아 슬라이딩 윈도우 방식으로 그룹화합니다.
    """
    def __init__(self, debug_mode=False, window_ms=100):
        self.debug_mode = debug_mode
        self.ports = get_arduino_ports(DEBUG_MODE=self.debug_mode)
        self.threads = []
        self.window_ms = window_ms  # 슬라이딩 윈도우 기간 (밀리초)
        self.all_data = []  # 모든 데이터를 모으는 중앙 버퍼
        self.all_data_lock = Lock()  # 공유 버퍼 보호를 위한 Lock
        # 슬라이딩 윈도우 처리를 위한 별도 스레드 생성
        self.sliding_thread = Thread(target=self.process_sliding_window, daemon=True)

    def start_threads(self):
        for i, port in enumerate(self.ports):
            print('make Serial', i, port)
            if port.startswith('V'):
                thread = SerialThreadVirtual(port, self.ports)
            else:
                thread = SerialThread(port)
            thread.start()
            self.threads.append(thread)
            print(f"Started thread for port: {port}")
        self.sliding_thread.start()

    def process_sliding_window(self):
        """
        각 스레드의 큐에서 데이터를 가져와 중앙 버퍼에 저장한 후,
        슬라이딩 윈도우 기간 내에 4개 포트의 데이터가 모이면 각 포트별 하나의 데이터만 선택해 그룹으로 처리합니다.
        """
        while True:
            # 각 스레드의 databuf에서 데이터 수집
            for thread in self.threads:
                while not thread.databuf.empty():
                    data_packet = thread.databuf.get()
                    # 데이터_packet: (timestamp, value, sub1, sub2)
                    with self.all_data_lock:
                        self.all_data.append({
                            "timestamp": data_packet[0],
                            "value": data_packet[1],
                            "sub1": data_packet[2],
                            "sub2": data_packet[3],
                            "Data_port_number": thread.port
                        })
            # 안전하게 데이터를 복사하고 원본 버퍼 초기화
            with self.all_data_lock:
                data_copy = self.all_data[:]  # 항상 data_copy를 빈 리스트 또는 복사된 리스트로 초기화
                self.all_data = []

            if data_copy:
                # 각 데이터의 timestamp를 datetime 객체로 변환
                for row in data_copy:
                    try:
                        ts_parts = row["timestamp"].split('_')
                        if len(ts_parts) == 4:
                            formatted_ts = f"{ts_parts[0]}:{ts_parts[1]}:{ts_parts[2]}.{ts_parts[3]}"
                        else:
                            formatted_ts = row["timestamp"]
                        today = datetime.datetime.now().strftime("%Y-%m-%d")
                        row["timestamp_dt"] = datetime.datetime.strptime(today + " " + formatted_ts,
                                                                         "%Y-%m-%d %H:%M:%S.%f")
                    except Exception as e:
                        print("타임스탬프 파싱 오류:", e)
                # 시간순으로 정렬
                data_copy.sort(key=lambda x: x["timestamp_dt"])
                i = 0
                n = len(data_copy)
                while i < n:
                    window_start = data_copy[i]["timestamp_dt"]
                    window = [data_copy[i]]
                    j = i + 1
                    while j < n and (
                            data_copy[j]["timestamp_dt"] - window_start).total_seconds() * 1000 <= self.window_ms:
                        window.append(data_copy[j])
                        j += 1
                    # 각 윈도우 내 포트 번호 추출
                    ports = [row["Data_port_number"] for row in window]
                    # 중복이 있으면 윈도우 폐기
                    if len(ports) != len(set(ports)):
                        print(f"{window_start}부터 시작하는 윈도우에 중복된 포트가 있어 폐기합니다.")
                    elif set(ports) == set(self.ports):
                        print("슬라이딩 윈도우 그룹 (포트별 1개 데이터):")
                        grouped = {}
                        for row in window:
                            port = row["Data_port_number"]
                            if port not in grouped:
                                grouped[port] = row
                        for port, data in grouped.items():
                            print(f"{port}: {data}")
                    else:
                        print("윈도우가 불완전합니다. 포함된 포트:", set(ports))
                        grouped = {}
                        for row in window:
                            port = row["Data_port_number"]
                            if port not in grouped:
                                grouped[port] = row
                        for port, data in grouped.items():
                            print(f"{port}: {data}")
                        print("----------")
                    i = j
            time.sleep(0.1)

    def stop_threads(self):
        for thread in self.threads:
            thread.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    serial_manager = SerialManager(debug_mode=True)
    serial_manager.start_threads()

    sys.exit(app.exec_())
