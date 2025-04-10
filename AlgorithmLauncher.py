from Algorithm.COGMassEstimation import COGMassEstimation
from Algorithm.MLPPredictor import KerasMLPPredictor
from Algorithm.RandomForestPredictor import RandomForestPredictor


def launch_algorithm(file_name):
    if file_name == "COGMassEstimation.py":
        algo = COGMassEstimation()
    elif file_name == "MLPPredictor.py":
        algo = KerasMLPPredictor()
    elif file_name == "RandomForestPredictor.py":
        algo = RandomForestPredictor()
    else:
        return

    algo.runProc()