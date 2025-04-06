import os
import copy
from queue import Queue, Empty
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal, QCoreApplication, QTimer
from PyQt5.QtWidgets import QApplication
import sys
import random
import datetime
from threading import Thread, Lock
import time
import threading



RAW_DATA_TEST_REPLAY = True # False 기존, True 임시값 전송

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "wch", "Serial"]):
            return port.device
    return None


def get_arduino_ports(DEBUG_MODE=False):
    if RAW_DATA_TEST_REPLAY:
        return [f"VCOM{i + 1}" for i in range(4)]

    ports = serial.tools.list_ports.comports()
    ports = [
        port.device for port in ports
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "Serial", "wch"])
    ]

    if DEBUG_MODE:
        remainNumofPort = 4 - len(ports)
        if len(ports) != 0 and remainNumofPort > 0:
            for i in range(remainNumofPort):
                ports.append('VCOM' + str(i + 1))
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
            offset_ms = random.randint(0, 20)
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
    ROS의 ApproximateTimeSynchronizer와 유사하게 4개의 센서(SerialThreadVirtual)에서 발생하는 데이터를 동기화합니다.

    각 센서에서 발생한 데이터는 다음 딕셔너리 형식으로 저장됩니다.
      {
          "timestamp": 원래 문자열 (예: "15_17_48_666"),
          "value": 센서 값,
          "sub1": 추가 센서 값,
          "sub2": 추가 센서 값,
          "Data_port_number": 센서 이름 (예: "VCOM1"),
          "timestamp_dt": datetime 객체 (오늘 날짜 기준)
      }

    동기화 알고리즘은 각 센서 버퍼에서 가장 오래된 메시지를 후보로 삼아,
    후보들 간의 타임스탬프 차이가 설정한 slop(초) 이하이면 동기화된 그룹으로 인정합니다.
    동기화된 그룹은 self.candidate_window 변수에 저장되고, callback 함수가 있으면 호출됩니다.
    """

    def __init__(self, sensor_ids=None, slop=0.1, callback=None):
        """
        sensor_ids: 센서 이름 리스트 (예: ["VCOM1", "VCOM2", "VCOM3", "VCOM4"])
        slop: 허용 오차 (초 단위)
        callback: 동기화된 그룹이 형성되면 호출할 함수 (예: sync_callback)
        """
        # self.sensor_ids = sensor_ids
        if sensor_ids is None:
            sensor_ids = get_arduino_ports(True)
        self.sensor_ids = sensor_ids
        self.slop = slop  # 초 단위 허용 오차
        self.callback = callback
        self.buffers = {sid: [] for sid in sensor_ids}
        self.lock = threading.Lock()
        self.candidate_window = {}  # 동기화된 그룹 저장

        # 각 센서별 스레드 생성 및 실행
        self.threads = []
        for sid in sensor_ids:
            thread = SerialThreadVirtual(sid, sensor_ids)
            thread.start()
            self.threads.append(thread)

        # 별도의 폴링 스레드에서 센서 스레드의 데이터를 버퍼에 저장
        self.poll_thread = threading.Thread(target=self.poll_sensors, daemon=True)
        self.poll_thread.start()

    def poll_sensors(self):
        """
        각 센서 스레드의 databuf에서 데이터를 읽어와서,
        각 센서별 버퍼(self.buffers)에 저장하고 동기화를 시도합니다.
        """
        while True:
            for thread in self.threads:
                try:
                    while True:
                        # 데이터 형식: (timestamp, value, sub1, sub2)
                        msg = thread.databuf.get_nowait()
                        sensor_id = thread.port
                        record = {
                            "timestamp": msg[0],
                            "value": msg[1],
                            "sub1": msg[2],
                            "sub2": msg[3],
                            "Data_port_number": sensor_id
                        }
                        # timestamp 문자열("HH_MM_SS_mmm")을 오늘 날짜 기준 datetime 객체로 변환
                        try:
                            ts_parts = record["timestamp"].split('_')
                            if len(ts_parts) == 4:
                                formatted_ts = f"{ts_parts[0]}:{ts_parts[1]}:{ts_parts[2]}.{ts_parts[3]}"
                            else:
                                formatted_ts = record["timestamp"]
                            today = datetime.datetime.now().strftime("%Y-%m-%d")
                            record["timestamp_dt"] = datetime.datetime.strptime(today + " " + formatted_ts,
                                                                                "%Y-%m-%d %H:%M:%S.%f")
                        except Exception as e:
                            print("Timestamp parsing error:", e)
                            continue

                        with self.lock:
                            self.buffers[sensor_id].append(record)
                            # 버퍼를 타임스탬프 기준으로 정렬
                            self.buffers[sensor_id].sort(key=lambda x: x["timestamp_dt"])
                        self.try_sync()
                except Empty:
                    pass
            time.sleep(0.01)

    def try_sync(self):
        """
        각 센서 버퍼의 가장 오래된 메시지를 후보로 선택하여,
        후보들의 타임스탬프 차이가 slop 이하이면 동기화된 그룹으로 처리합니다.
        """
        with self.lock:
            # 모든 센서에 최소 한 개의 데이터가 있어야 시도
            if not all(self.buffers[sid] for sid in self.sensor_ids):
                return

            candidate = {sid: self.buffers[sid][0] for sid in self.sensor_ids}
            times = [rec["timestamp_dt"] for rec in candidate.values()]
            t_min = min(times)
            t_max = max(times)
            elapsed = (t_max - t_min).total_seconds()
            if elapsed <= self.slop:
                self.candidate_window = candidate.copy()
                # 각 센서 버퍼에서 사용한 데이터 제거
                for sid in self.sensor_ids:
                    self.buffers[sid].pop(0)
                if self.callback:
                    self.callback(self.candidate_window)
            else:
                # 동기화 조건 미달 시, 가장 오래된 데이터를 버림
                oldest_sensor = min(self.sensor_ids, key=lambda s: self.buffers[s][0]["timestamp_dt"])
                dropped = self.buffers[oldest_sensor].pop(0)
                print(f"[Dropped] Sensor {oldest_sensor} data {dropped} dropped; elapsed: {elapsed:.3f} seconds")


def sync_callback(group):
    print("Synchronized group:")
    for sensor, record in group.items():
        print(f"{sensor}: {record}")
    print("----")


if __name__ == "__main__":
    # app = QCoreApplication(sys.argv)

    synchronizer = SerialManager(slop=0.1, callback=sync_callback)
    print("SerialManager started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
