#!/usr/bin/env python
import esteam
from setuptools import setup


setup(name='esteam',
      version=esteam.__version__,
      description='Steam Card Farmer.',
      author='lux.r.ck',
      author_email='lux.r.ck@gmail.com',
      packages=['esteam', 'esteam.schedulers'],
      entry_points={
        "console_scripts": "esteam = esteam.__main__:main"
        },
      install_requires=[
        "lxml",
        "aiosteam",
        "sanic",
        ],
      include_package_data=True,
      license="MIT License",
      zip_safe=False,
     )
