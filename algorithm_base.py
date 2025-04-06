# 📁 algorithm_base.py

from abc import ABC, abstractmethod
import time
from typing import Dict, Any, Optional, List


class AlgorithmBase(ABC):
    def __init__(self, name: str, description: str = "", model_path: str = ""):
        self.name = name
        self.description = description
        self.model_path = model_path
        self.input_data = {}
        self.output_data = {}
        self.execution_time = 0
        self.is_running = False
        self.execution_history = []

    @abstractmethod
    def process(self) -> Dict[str, Any]:
        pass

    def set_input_data(self, data: Dict[str, Any]) -> None:
        self.input_data = data

    def get_output_data(self) -> Dict[str, Any]:
        return self.output_data

    def get_history(self) -> List[Any]:
        return self.execution_history

    def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            self.is_running = True
            start_time = time.time()

            if input_data is not None:
                self.set_input_data(input_data)

            results = self.process()
            self.output_data = results
            self.execution_time = time.time() - start_time

            self.execution_history.append({
                'timestamp': time.time(),
                'input_keys': list(self.input_data.keys()),
                'output_keys': list(self.output_data.keys()),
                'execution_time': self.execution_time
            })

            return self.output_data
        finally:
            self.is_running = False

    def clear_data(self) -> None:
        self.input_data = {}
        self.output_data = {}
