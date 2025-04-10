from queue import Queue, Empty
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication
import sys
import random
import datetime
from threading import Thread, Lock
import time


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "wch", "Serial"]):
            return port.device
    return None


def get_arduino_ports(DEBUG_MODE=False):
    if DEBUG_MODE:
        return [f"VCOM{i + 1}" for i in range(4)]
    ports = serial.tools.list_ports.comports()
    ports = [
        port.device for port in ports
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "Serial", "wch"])
    ]
    return ports


class SensorData():
    def __init__(self, sname, serialport, timestamp, value, sub_part1, sub_part2):
        """
        sname : 센서명
        serialport : 시리얼포트
        timestamp : 시간값
        value : 센서값
        sub1 : 추가 센서값
        sub2 : 추가 센서값
        """
        self.sname = sname
        self.serialport = serialport
        self.timestamp = timestamp
        self.value = value
        self.sub1 = sub_part1
        self.sub2 = sub_part2

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
        if not self.port:
            print("아두이노 포트를 찾을 수 없습니다.")
            return
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        except Exception as e:
            print(f"포트 {self.port} 열기 실패: {e}")
            return

        while self.is_running:
            if not self.is_paused and self.ser.in_waiting > 0:
                try:
                    data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                except Exception as e:
                    print(f"데이터 수신 오류: {e}")
                    continue

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

                    sdata = SensorData("Laser", self.port, timestamp, value, sub_part1, sub_part2)

                    # self.databuf.put((timestamp, value, sub_part1, sub_part2))
                    self.databuf.put(sdata)
            self.msleep(1)

    def pause(self):
        self.is_paused = True

    def resume(self):
        if hasattr(self, 'ser'):
            self.ser.flushInput()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()


class SerialThreadVirtual(SerialThread):
    def __init__(self, port):
        super().__init__(port)

    def run(self):
        try:
            pidxGap = int(''.join(filter(str.isdigit, self.port))) - 1
        except ValueError:
            pidxGap = 0

        while self.is_running:
            base_time = datetime.datetime.now()
            offset_ms = random.randint(0, 0)   # 랜덤 오프셋
            timestamp_dt = base_time + datetime.timedelta(milliseconds=offset_ms)
            # 타임스탬프 포맷: "HH_MM_SS_mmm"
            timestamp = timestamp_dt.strftime("%H_%M_%S_%f")[:-3]

            value = random.randint(400+(pidxGap*10), 450+(pidxGap*10))
            sub_part1 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part2 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))

            sdata = SensorData("Laser", self.port, timestamp, value, sub_part1, sub_part2)

            # self.databuf.put((timestamp, value, sub_part1, sub_part2))

            # self.databuf.put((timestamp, value, sub_part1, sub_part2))
            self.databuf.put(sdata)
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
    def __init__(self, debug_mode, slop=0.1, callback=None):
        self.debug_mode = debug_mode
        self.ports = get_arduino_ports(self.debug_mode)
        self.slop = slop  # 초 단위 허용 오차
        self.callback = callback
        self.buffers = {port: [] for port in self.ports}
        self.lock = Lock()
        self.candidate_window = {}  # 동기화된 그룹 저장

        # 각 포트별 스레드 생성 및 실행
        self.threads = []

        # 공유 큐들을 저장할 리스트
        self.algo_buffers = []  # 각 요소는 알고리즘에서 전달받은 Queue 객체

    def add_buffer(self, buffer):
        with self.lock:
            if buffer not in self.algo_buffers:
                self.algo_buffers.append(buffer)

    def remove_buffer(self, buffer):
        with self.lock:
            if buffer in self.algo_buffers:
                self.algo_buffers.remove(buffer)

    def start_threads(self):
        for port in self.ports:
            if self.debug_mode:
                thread = SerialThreadVirtual(port)
            else:
                thread = SerialThread(port)
            thread.start()
            self.threads.append(thread)

        # 별도의 폴링 스레드에서 센서 스레드의 데이터를 버퍼에 저장
        self.poll_thread = Thread(target=self.poll_sensors, daemon=True)
        self.poll_thread.start()

    def poll_sensors(self):
        """
        각 센서 스레드의 databuf에서 데이터를 읽어와서,
        각 포트별 버퍼(self.buffers)에 저장하고 동기화를 시도합니다.
        """
        while True:
            for thread in self.threads:
                try:
                    while True:
                        # 데이터 형식: (timestamp, value, sub1, sub2)
                        msg = thread.databuf.get_nowait()
                        port = thread.port
                        record = {
                            "timestamp": msg.timestamp,
                            "value": msg.value,
                            "sub1": msg.sub1,
                            "sub2": msg.sub2,
                            "port": port
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
                            self.buffers[port].append(record)
                            self.buffers[port].sort(key=lambda x: x["timestamp_dt"])
                        self.try_sync()
                except Empty:
                    pass
            time.sleep(0.01)

    def try_sync(self):
        """
        각 포트 버퍼의 가장 오래된 메시지를 후보로 선택하여,
        후보들의 타임스탬프 차이가 slop 이하이면 동기화된 그룹으로 처리합니다.
        """
        with self.lock:
            if not all(self.buffers[port] for port in self.ports):
                return

            candidate = {port: self.buffers[port][0] for port in self.ports}
            times = [rec["timestamp_dt"] for rec in candidate.values()]
            t_min = min(times)
            t_max = max(times)
            elapsed = (t_max - t_min).total_seconds()
            if elapsed <= self.slop:
                self.candidate_window = candidate.copy()
                for port in self.ports:
                    self.buffers[port].pop(0)
                if self.callback:
                    self.callback(self.candidate_window)
                for buf in self.algo_buffers:
                    buf.put(candidate.copy())
                print(self.algo_buffers)
            else:
                oldest_port = min(self.ports, key=lambda p: self.buffers[p][0]["timestamp_dt"])
                dropped = self.buffers[oldest_port].pop(0)
                # print(f"[Dropped] Sensor {oldest_port} data {dropped} dropped; elapsed: {elapsed:.3f} seconds")

    def getCandidate(self):
        if len(self.candidate_window) == 4:
            return self.candidate_window

    def stop_threads(self):
        for thread in self.threads:
            thread.stop()

def sync_callback(group):
    print("Synchronized group:")
    for port, record in group.items():
        print(f"{port}: {record}")
    print("----")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # synchronizer = SerialManager(debug_mode=True, slop=0.1, callback=sync_callback)
    synchronizer = SerialManager(debug_mode=True, slop=0.1)
    synchronizer.start_threads()
    print("SerialManager started.")
    sys.exit(app.exec_())
