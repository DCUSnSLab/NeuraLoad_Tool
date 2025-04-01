import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
import sys

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "wch", "Serial"]):
            return port.device
    return None

def get_arduino_ports():
    ports = serial.tools.list_ports.comports()
    return [
        port.device for port in ports
        if any(keyword in port.description for keyword in ["Arduino", "USB", "CH340", "Serial", "wch"])
    ]

class SerialThread(QThread):
    data_received = pyqtSignal(str, str)

    def __init__(self, port=None, baudrate=9600):
        super().__init__()
        self.port = port or find_arduino_port()
        self.baudrate = baudrate
        self.is_running = True
        self.is_paused = False
        self.last_data = "0"

    def run(self):
        if not self.port:
            print("아두이노 포트를 찾을 수 없습니다.")
            return
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)

            while self.is_running:
                if not self.is_paused and self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        self.last_data = data

                # pause 여부 상관없이 계속 emit
                self.data_received.emit(self.port, self.last_data)
                self.msleep(100)  # 그래프는 계속 움직이게

        except serial.serialutil.SerialException as e:
            print(f"시리얼 연결 오류: {e}")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.ser.flushInput()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ports = get_arduino_ports()

    threads = []

    for port in get_arduino_ports():
        thread = SerialThread(port=port)
        thread.start()
        threads.append(thread)

    sys.exit(app.exec_())