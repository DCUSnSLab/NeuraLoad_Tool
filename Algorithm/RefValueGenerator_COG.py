from Algorithm.RefValueGenerator import RefValueGenerator
from datainfo import SensorFrame, SENSORLOCATION

class COGRefValGenerator(RefValueGenerator):
    def __init__(self):
        super().__init__()
        print('COGMassEstimation Refer Value Generator')
        self.initCheck = True
        self.ti_start = 0
        self.ti_end = 50
        self.tl_buf = []
        self.bl_buf = []
        self.tr_buf = []
        self.br_buf = []
    def calRefValue(self, input: SensorFrame):
        if self.initCheck:
            self.tl_buf.append(input.get_sensor_data(SENSORLOCATION.TOP_LEFT).distance)
            self.bl_buf.append(input.get_sensor_data(SENSORLOCATION.BOTTOM_LEFT).distance)
            self.tr_buf.append(input.get_sensor_data(SENSORLOCATION.TOP_RIGHT).distance)
            self.br_buf.append(input.get_sensor_data(SENSORLOCATION.BOTTOM_RIGHT).distance)
            self.ti_start += 1

            if self.ti_start >= self.ti_end:
                self.initCheck = False
                avg_tl = sum(self.tl_buf) / len(self.tl_buf)
                avg_bl = sum(self.bl_buf) / len(self.bl_buf)
                avg_tr = sum(self.tr_buf) / len(self.tr_buf)
                avg_br = sum(self.br_buf) / len(self.br_buf)
                self._refValue = [int(avg_tl), int(avg_bl), int(avg_tr), int(avg_br)]