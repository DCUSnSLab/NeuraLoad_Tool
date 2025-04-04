import os
from queue import Queue
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
import sys
import random
import datetime

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "wch", "Serial"]):
            return port.device
    return None

def get_arduino_ports(DEBUG_MODE=False):
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
                    main_part = parts[0].strip()
                    sub_part1 = parts[1].strip()
                    sub_part2 = parts[2].strip()

                    if not main_part.isdigit():
                        return
                    value = int(main_part)

                    # print(value, self.databuf.qsize())
                    # self.save(timestamp, value, sub_part1, sub_part2)
                    self.databuf.put((timestamp, value, sub_part1, sub_part2))

            self.msleep(1)

    def pause(self):
        self.is_paused = True

    def resume(self):
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
            timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]
            value = random.randint(400+(pidxGap*10), 450+(pidxGap*10))
            sub_part1 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            sub_part2 = random.randint(400 + (pidxGap * 10), 450 + (pidxGap * 10))
            self.databuf.put((timestamp, value, sub_part1, sub_part2))
            self.msleep(100)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ports = get_arduino_ports()

    threads = []

    for port in get_arduino_ports():
        thread = SerialThread(port=port)
        thread.start()
        threads.append(thread)

    sys.exit(app.exec_())