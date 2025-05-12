from Algorithm.RefValueGenerator import RefValueGenerator
from datainfo import SensorFrame, SENSORLOCATION

class COGRefValGenerator(RefValueGenerator):
    def __init__(self):
        super().__init__()
        print('COGMassEstimation Refer Value Generator')
        self.initCheck = True

    def calRefValue(self, input: SensorFrame):
        if self.initCheck == True:
            # 센서 값 추출
            laser_values = [
                input.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance,
                input.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance,
                input.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance,
                input.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance,
            ]
            if all(v not in [-1, 0] for v in laser_values):
                self.initCheck = False
                self._refValue = laser_values

