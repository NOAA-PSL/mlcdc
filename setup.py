from setuptools import setup

install_requires=[
        "xarray",
        "zarr",
        "numpy",
]

setup(
        name="mlcdc",
        description="Machine Learning for estimating Cross Domain Correlations",
        url="https://github.com/noaa-psd/mlcdc",
        author="Zofia Stanely & Timothy Smith",
        install_requires=install_requires,
)
