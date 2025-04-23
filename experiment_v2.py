from PyQt5.QtWidgets import QWidget

from arduino_manager import SerialManager, Sensor

class ExperimentData():
    def __init__(self, dataManager: 'SerialManager'):
        self.sensors = dict()

        self.graphYAxisMax = 800
        self.graphYAxisMin = 0



        self.__initSensors(dataManager.getSensors())

    def __initSensors(self, sens: 'Sensor'):
        for sensor in sens:
            self.sensors[sensor.sensorLoc] = sensor

class ExperimentTab(QWidget):
    def __init__(self, dataManager):
        super().__init__()
        self.dataManager = dataManager
        self.expData = ExperimentData(self.dataManager)
