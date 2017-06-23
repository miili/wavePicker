# wavePicker

**This Project is not supported anymore, see http://pyrocko.org Snuffler for seismic data inspection and picking!**

A Seismic Wave Time Arrival Picker for ObsPy Stream Objects

This library aims to be a useful picker for `obspy.core.Stream` objects.
wavePicker utilizes the following libraries:
* ObsPy
* PySide
* pyqtgraph

*Make sure to apply this simple patch to pyqtgraph before starting!!*

https://github.com/pyqtgraph/pyqtgraph/pull/142

## Installation

try `python setup.py intall`

be aware that compilation of `pyside` can take a long time

## Features

* Fast data visualisation through `pyqtgraph`
* Earthquake Event Management
* Save/Load Picks in JSON format
* Export Stations and Phases to Hypoinverse2000 format

## Screenshots
![wavepicker-gui](https://cloud.githubusercontent.com/assets/4992805/5938686/82c7adb2-a70e-11e4-911a-67137247642e.png)

![wavepicker-gui_filter](https://cloud.githubusercontent.com/assets/4992805/5938703/a5e530d0-a70e-11e4-9f95-b9679813b09c.png)
