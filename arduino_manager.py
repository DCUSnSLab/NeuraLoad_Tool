import os
import copy
import re
from queue import Queue, Empty
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QCoreApplication, QTimer
from PyQt5.QtWidgets import QApplication
import sys
import random
import datetime
from threading import Thread, Lock
import time

from datainfo import SensorData, SENSORLOCATION


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

class Sensor(QThread):
    errorSignal = pyqtSignal(str)  #serialManager에 전달하는 시그널

    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.is_running = True
        self.is_paused = False

        self.databuf = Queue(maxsize=1000)
        self.weight_a = [0] * 9
        self.refValue = -1

        self.sensorInitted = False
        self.serial = None
        self.port = port or find_arduino_port()
        self.baudrate = baudrate
        self.sensorLoc = SENSORLOCATION.NONE
        self._initSensor()

    def _initSensor(self):
        if not self.port:
            print("아두이노 포트를 찾을 수 없습니다.")
            self.errorSignal.emit("아두이노 포트를 찾을 수 없습니다.")
            return
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
        except Exception as e:
            print(f"포트 {self.port} 열기 실패: {e}")
            self.errorSignal.emit(f"port {self.port} open fail: {e}")
            return

        #get first Data from sensor
        data = None
        while data is None:
            data = self.__getDatafromSerial()
            self.msleep(1)

        #set sensor location
        if self._setSensorLoc(data) is True:
            self.sensorInitted = True

        #set sensor reference value
        self.refValue = data.value

    def _setSensorLoc(self, data: 'SensorData'):
        if data is not None:
            self.sensorLoc = data.getSensorLoc()


    def run(self):
        while self.sensorInitted is True and self.is_running is True:
            try:
                if not self.is_paused and self.serial.in_waiting > 0:
                        resData = self.__getDatafromSerial()
                        if resData is not None:
                            self.databuf.put(resData)
                self.msleep(1)
            except serial.SerialException:
                print('센서 연결 끊김')
                self.errorSignal.emit("센서 연결 끊김")
                break

    def __getDatafromSerial(self):
        try:
            data = self.serial.readline().decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"데이터 수신 오류: {e}")
            return None
        timestamp = datetime.datetime.now()
        if data:
            parts = data.split(',')
            if len(parts) < 4:
                return None
            location = parts[0].strip()
            value = parts[1].strip()
            sub_part1 = parts[2].strip()
            sub_part2 = parts[3].strip()

            if not value.isdigit() and not location.isdigit():
                return None
            value = int(value)
            location = int(location)

            sdata = SensorData("Laser", self.port, timestamp, location, value, sub_part1, sub_part2)
            self.databuf.put(sdata)
            return sdata
        else:
            return None

    def pause(self):
        self.is_paused = True

    def resume(self):
        if hasattr(self, 'ser'):
            self.ser.flushInput()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()


class SensorVirtual(Sensor):
    errorSignal = pyqtSignal(str)

    def __init__(self, port):
        super().__init__(port)

    def _initSensor(self):
        if self._setSensorLoc() is True:
            self.sensorInitted = True

        # set sensor reference value
        self.refValue = 700

    def _setSensorLoc(self):
        pnum = self.__extract_number(self.port) - 1
        self.sensorLoc = SENSORLOCATION.get_sensor_location(pnum)
        if self.sensorLoc != SENSORLOCATION.NONE:
            return True
        else:
            return False

    def __extract_number(self, port: str) -> int:
        match = re.search(r'\d+', port)
        if match:
            return int(match.group())
        else:
            raise ValueError(f"No number found in port string: {port}")

    def run(self):
        try:
            pidxGap = int(''.join(filter(str.isdigit, self.port))) - 1
        except ValueError:
            pidxGap = 0

        # test를 위한 시그널 전송
        # self.errorSignal.emit("virtual start")

        while self.is_running:
            base_time = datetime.datetime.now()
            offset_ms = random.randint(0, 20)   # 랜덤 오프셋
            timestamp = base_time + datetime.timedelta(milliseconds=offset_ms)

            value = random.randint(600 + (pidxGap * 10), 700 + (pidxGap * 10))
            sub_part1 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part2 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))

            sdata = SensorData("Laser", self.port, timestamp, value, sub_part1, sub_part2)

            self.databuf.put(sdata)
            self.msleep(100)


class SerialManager(QObject):
    """
    ROS의 ApproximateTimeSynchronizer와 유사하게 4개의 센서에서 발생하는 데이터를 동기화
    동기화 알고리즘은 각 센서 버퍼에서 가장 오래된 메시지를 후보로 삼아,
    후보들 간의 타임스탬프 차이가 설정한 slop(초) 이하이면 동기화된 그룹으로 인정
    ndi동기화된 그룹은 self.cadate_window 변수에 저장됨
    """

    errorSignal = pyqtSignal(str)  # Sensor에서 발생하는 에러 메시지를 main에 전송하기 위한 시그널
    def __init__(self, debug_mode, slop=0.1, callback=None):
        super().__init__()  # QObject상속을 위한 호출 (pyqtSignal사용을 위해 QObject상속)
        self.debug_mode = debug_mode
        self.ports = get_arduino_ports(self.debug_mode)
        self.slop = slop  # 초 단위 허용 오차
        self.callback = callback
        self.buffers = {port: [] for port in self.ports}
        self.lock = Lock()
        self.candidate_window = {}  # 동기화된 그룹 저장

        # 각 포트별 스레드 생성 및 실행
        self.sensors = []

        # 공유 큐들을 저장할 리스트
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
                sensor = SensorVirtual(port)
            else:
                sensor = Sensor(port)
            sensor.errorSignal.connect(self.hadleThreadSignal)  # 시그널과 연결될 함수
            sensor.start()
            self.sensors.append(sensor)

        # 별도의 폴링 스레드에서 센서 스레드의 데이터를 버퍼에 저장
        self.poll_thread = Thread(target=self.poll_sensors, daemon=True)
        self.poll_thread.start()

    def hadleThreadSignal(self, massage):
        self.errorSignal.emit(massage)

    def poll_sensors(self):
        """
        각 센서 스레드의 databuf에서 데이터를 읽어
        각 포트별 버퍼(self.buffers)에 저장하고 동기화를 시도합니다.
        """
        while True:
            for sensor in self.sensors:
                try:
                    while True:
                        sdata = sensor.databuf.get_nowait()  # sdata : SensorData 객체
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

            candidate_list = [self.buffers[port][0] for port in self.ports]
            times = [obj.timestamp for obj in candidate_list]

            if (max(times) - min(times)).total_seconds() <= self.slop:
                self.candidate_window = candidate_list.copy()
                for port in self.ports:
                    self.buffers[port].pop(0)
                if self.callback:
                    self.callback(self.candidate_window)
                for buf in self.algo_buffers:
                    buf.put(self.candidate_window.copy())
                self.exper_buffer.put(self.candidate_window.copy())
            else:
                oldest_port = min(self.ports, key=lambda p: self.buffers[p][0].timestamp)
                dropped = self.buffers[oldest_port].pop(0)
                # print(f"[Dropped] Sensor {oldest_port} data {dropped} dropped")

    def getCandidate(self):
        if len(self.candidate_window) == len(self.ports):
            return self.candidate_window

    def stop_threads(self):
        for thread in self.sensors:
            thread.stop()

    def getSensors(self):
        return self.sensors

def sync_callback(group):
    print("Synchronized group:")
    for data in group:
        print(f"{data.serialport}: (Timestamp: {data.timestamp}, port_index: {data.port_index}, value: {data.value}, sub1: {data.sub1}, sub2: {data.sub2})")
    print("----")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    synchronizer = SerialManager(debug_mode=True, slop=0.1, callback=sync_callback)
    # synchronizer = SerialManager(debug_mode=True, slop=0.1)
    synchronizer.start_threads()
    print("SerialManager started.")
    sys.exit(app.exec_())
