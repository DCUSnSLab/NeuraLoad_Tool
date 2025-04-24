from Algorithm.RefValueGenerator import RefValueGenerator
from datainfo import SensorFrame


class COGRefValGenerator(RefValueGenerator):
    def __init__(self):
        super().__init__()
        print('COGMassEstimation Refer Value Generator')

    def calRefValue(self, input:SensorFrame):
        self._refValue = [10] * 9 #for test