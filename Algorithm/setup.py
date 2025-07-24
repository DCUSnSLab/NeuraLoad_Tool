from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os

this_dir = os.path.abspath(os.path.dirname(__file__))

assert os.path.exists(os.path.join(this_dir, "COGMassEstimation.c")), "COGMassEstimation.c not found!"

ext_modules = [
    Extension(
        "cog_estimation",
        sources=[
            os.path.join(this_dir, "cog_estimation.pyx"),
            os.path.join(this_dir, "COGMassEstimation.c")
        ],
        include_dirs=[np.get_include(), this_dir],
    )
]

setup(
    name="cog_estimation",
    ext_modules=cythonize(ext_modules, language_level=3),
    include_dirs=[np.get_include()]
)
