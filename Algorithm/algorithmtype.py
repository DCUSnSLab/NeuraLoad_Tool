from enum import Enum


class ALGORITHM_TYPE(Enum):
    COGMassEstimation = 0
    MLPPredictor = 1
    RandomForestPredictor = 2

    @staticmethod
    def get_sensor_location(value: int) -> 'ALGORITHM_TYPE':
        return ALGORITHM_TYPE(value)