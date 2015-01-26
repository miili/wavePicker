import os
from setuptools import setup
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name='grapePicker',
	version='0.1dev',
	author='Marius P Isken',
	author_email='github@mail',
	description='A Seismic Wave Time Arrival Picker for ObsPy Stream Objects',
	license='GNUv2',
	keywords='seismology traveltime hypocenter hypoinverse2000 obspy',
	url='https://github.com/miili/grapePicker',
	long_description=read('README.md'),
	packages=['grapePicker']
	#install_requires=['pyqtgraph', 'pyside', 'obspy']
	)