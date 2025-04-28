from Algorithm.RefValueGenerator import RefValueGenerator
from datainfo import SensorFrame, SENSORLOCATION


class COGRefValGenerator(RefValueGenerator):
    def __init__(self):
        super().__init__()
        print('COGMassEstimation Refer Value Generator')

    def compute_deltas(self, current_values):
        # 초기 값이 설정되지 않았다면 현재 값을 초기 값으로 설정
        if not hasattr(self, 'initial_laser_values'):
            if all(v not in [-1, 0] for v in current_values):
                self.initial_laser_values = current_values
                return [0] * len(current_values)
            else:
                return [0] * len(current_values)

        # 변화량 계산
        deltas = [init - curr for curr, init in zip(current_values, self.initial_laser_values)]
        return deltas

    def calRefValue(self, input: SensorFrame):
        # 센서 값 추출
        laser_values = [
            input.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance,
            input.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance,
            input.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance,
            input.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance,
        ]

        # 변화량 계산
        deltas = self.compute_deltas(laser_values)
        # 변화량을 _refValue에 저장
        self._refValue = deltas
        return self._refValue