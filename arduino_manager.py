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
    def __init__(self, sname, serialport, timestamp, port_index, value, sub_part1, sub_part2):
        """
        sname : 센서명
        serialport : 시리얼포트
        timestamp : 시간값
        port_index: 0,1,2,3 중 하나. 실제 부착된 센서 위치 식별
        value : 센서값
        sub1 : 추가 센서값
        sub2 : 추가 센서값
        """
        self.sname = sname
        self.serialport = serialport
        self.timestamp = timestamp
        self.port_index = port_index
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
            try:
                if not self.is_paused and self.ser.in_waiting > 0:
                    try:
                        data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    except Exception as e:
                        print(f"데이터 수신 오류: {e}")
                        continue

                    timestamp = datetime.datetime.now()
                    if data:
                        parts = data.split(',')
                        if len(parts) < 4:
                            continue
                        port_index = parts[0].strip()
                        value = parts[1].strip()
                        sub_part1 = parts[2].strip()
                        sub_part2 = parts[3].strip()

                        if not value.isdigit() and not port_index.isdigit():
                            continue
                        value = int(value)
                        port_index = int(port_index)

                        sdata = SensorData("Laser", self.port, timestamp, port_index, value, sub_part1, sub_part2)
                        self.databuf.put(sdata)
                self.msleep(1)
            except serial.SerialException:
                print('센서 연결 끊김')
                break

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
            pidx = int(''.join(filter(str.isdigit, self.port))) - 1
            port_index = pidx if 0 <= pidx < 4 else 0
        except ValueError:
            port_index = 0

        while self.is_running:
            base_time = datetime.datetime.now()
            offset_ms = random.randint(0, 20)   # 랜덤 오프셋
            timestamp = base_time + datetime.timedelta(milliseconds=offset_ms)

            value = random.randint(600 + (port_index * 10), 700 + (port_index * 10))
            sub_part1 = random.randint(400 + (port_index * 10), 450 + (port_index * 10))
            sub_part2 = random.randint(400 + (port_index * 10), 450 + (port_index * 10))

            sdata = SensorData("Laser", self.port, timestamp, port_index, value, sub_part1, sub_part2)

            self.databuf.put(sdata)
            self.msleep(100)


class SerialManager:
    """
    ROS의 ApproximateTimeSynchronizer와 유사하게 4개의 센서에서 발생하는 데이터를 동기화
    동기화 알고리즘은 각 센서 버퍼에서 가장 오래된 메시지를 후보로 삼아,
    후보들 간의 타임스탬프 차이가 설정한 slop(초) 이하이면 동기화된 그룹으로 인정
    ndi동기화된 그룹은 self.cadate_window 변수에 저장됨
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

        # 공유 큐
        self.algo_buffers = []  # 각 요소는 알고리즘에서 전달받은 Queue 객체
        self.exper_buffer = Queue()

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
        각 센서 스레드의 databuf에서 데이터를 읽어
        각 포트별 버퍼(self.buffers)에 저장하고 동기화를 시도합니다.
        """
        while True:
            for thread in self.threads:
                try:
                    while True:
                        sdata = thread.databuf.get_nowait()  # sdata : SensorData 객체
                        port = sdata.serialport
                        with self.lock:
                            self.buffers[port].append(sdata)
                            self.buffers[port].sort(key=lambda x: x.timestamp)
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
            times = [obj.timestamp for obj in candidate.values()]
            if (max(times) - min(times)).total_seconds() <= self.slop:
                self.candidate_window = candidate.copy()
                for port in self.ports:
                    self.buffers[port].pop(0)
                if self.callback:
                    self.callback(self.candidate_window)
                for buf in self.algo_buffers:
                    buf.put(candidate.copy())
                self.exper_buffer.put(candidate.copy())
            else:
                oldest_port = min(self.ports, key=lambda p: self.buffers[p][0].timestamp)
                self.buffers[oldest_port].pop(0)
                # print(f"[Dropped] Sensor {oldest_port} data {dropped} dropped; elapsed: {elapsed:.3f} seconds")

    def getCandidate(self):
        if len(self.candidate_window) == len(self.ports):
            return self.candidate_window

    def stop_threads(self):
        for thread in self.threads:
            thread.stop()

def sync_callback(group):
    print("Synchronized group:")
    for port, record in group.items():
        print(f"{port}: (Timestamp: {record.timestamp}, port_index: {record.port_index}, value: {record.value}, sub1: {record.sub1}, sub2: {record.sub2})")
    print("----")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    synchronizer = SerialManager(debug_mode=True, slop=0.1, callback=sync_callback)
    # synchronizer = SerialManager(debug_mode=True, slop=0.1)
    synchronizer.start_threads()
    print("SerialManager started.")
    sys.exit(app.exec_())
