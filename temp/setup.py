# setup.py
from distutils.core import setup, Extension

setup(name='HX711',
      ext_modules=[
        Extension('HX711',
                  ['HX711.cpp', 'pyHX711.cpp'],
                  include_dirs = ['./'],
                  library_dirs = ['./','/usr/local/lib'],
                  libraries = ['wiringPi']
                  )
        ]
)
