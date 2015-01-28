import os
from setuptools import setup
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name='wavePicker',
	version='0.1dev',
	author='Marius P Isken',
	author_email='github@mail',
	description='A Seismic Wave Time Arrival Picker for ObsPy Stream Objects',
	license='GNUv2',
	keywords='seismology traveltime hypocenter hypoinverse2000 obspy seismicity',
	url='https://github.com/miili/wavePicker',
	long_description=read('README.md'),
	packages=['wavePicker'],
	package_data={'wavePicker': ['icons/*.png']}
	#install_requires=['pyqtgraph', 'pyside', 'obspy']
	)
