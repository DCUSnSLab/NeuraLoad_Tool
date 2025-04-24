from typing_extensions import List

from datainfo import SensorFrame


class RefValueGenerator:
    def __init__(self):
        self._refValue: List[int] = [0] * 9

    def calRefValue(self, input:SensorFrame):
        pass

    def getRefValue(self):
        return self._refValue