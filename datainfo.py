from enum import Enum


class SENSORLOCATION(Enum):
    TOP_LEFT = 0
    BOTTOM_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_RIGHT = 3
    NONE = -1

    @staticmethod
    def get_sensor_location(value: int) -> 'SENSORLOCATION':
        try:
            return SENSORLOCATION(value)
        except ValueError:
            raise ValueError(f"Invalid sensor location value: {value}")


class SensorData():
    def __init__(self, sname, serialport, timestamp, loc, value, sub_part1, sub_part2):
        """
        sname : 센서명
        serialport : 시리얼포트
        timestamp : 시간값
        location : 센서 부착된 위치(0, 1, 2, 3)
        value : 센서값
        sub1 : 추가 센서값
        sub2 : 추가 센서값
        """
        self.sname = sname
        self.serialport = serialport
        self.timestamp = timestamp
        self.location = SENSORLOCATION.get_sensor_location(loc)
        self.value = value
        self.sub1 = sub_part1
        self.sub2 = sub_part2

    def getSensorLoc(self):
        return self.location