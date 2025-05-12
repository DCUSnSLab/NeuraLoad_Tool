from enum import Enum
from typing import List

class ALGORITHM_TYPE(Enum):
    COGMassEstimation = 0
    MLPPredictor = 1
    RandomForestPredictor = 2
    COGPositionMassEstimation = 3
    COGPositionMassEstimation_v2 = 4
    COGPositionMassEstimation_v3 = 5
    @staticmethod
    def get_algorithmTypebyValue(value: int) -> 'ALGORITHM_TYPE':
        return ALGORITHM_TYPE(value)

    @staticmethod
    def from_name(name: str) -> 'ALGORITHM_TYPE':
        try:
            return ALGORITHM_TYPE[name]
        except KeyError:
            raise ValueError(f"'{name}' is not a valid ALGORITHM_TYPE name")

    @staticmethod
    def list_all() -> List['ALGORITHM_TYPE']:
        return list(ALGORITHM_TYPE)