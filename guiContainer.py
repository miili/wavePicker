from PySide.QtGui import *
from PySide.QtCore import *

from obspy.core import UTCDateTime, Stream

import pyqtgraph as pg

import os

class Channel(object):
    '''
    Channel Container Object handels an individual channel

    self._qTreeStationChannel represents the QTreeWidgetItem
    self.traceItem is the inherited pyqtgraph.PlotCurveItem
    '''
    def __init__(self, tr, station):
        '''
        init the channel with parent Station() and obspy trace

        :tr: obspy.core.trace
        :station: Station()
        '''
        self.tr = tr
        self.station = station
        self.channel = tr.stats.channel

        self._qTreeStationChannel = QTreeWidgetItem()
        self._qTreeStationChannel.setText(1, '%s @ %d Hz' %
                                         (self.tr.stats.channel,
                                          1./self.tr.stats.delta))
        self._qTreeStationChannel.setText(2, '%s\n%s' %
                                         (self.tr.stats.starttime,
                                          self.tr.stats.endtime))
        self._qTreeStationChannel.setFont(1, QFont('', 8))
        self._qTreeStationChannel.setFont(2, QFont('', 8))
        self.station._qTreeStationItem.addChild(self._qTreeStationChannel)

    def plotTraceItem(self):
        '''
        Plots the pg.PlotCurveItem into self.station.plotItem
        '''
        self.plotTrace = self.tr.copy()
        # Filter if necessary
        if self.station.parent.parent.filterArgs is not None:
            self.plotTrace.filter('bandpass',
                                  **self.station.parent.parent.filterArgs)
        self.traceItem.setData(y=self.plotTrace.data, antialias=True)
        self.station.plotItem.getAxis('bottom').setScale(self.tr.stats.delta)

    def plotPickItems(self):
        '''
        Gets a list of Picks() and plots them
        accordingly in self.station.plotItem

        should be moved into Station()?
        '''
        _currentPlotItems = self.station.plotItem.getViewBox().allChildren()
        for pick in self.station.getPicks():
            if pick not in _currentPlotItems:
                self.station.plotItem.addItem(pick.getPickItem(self))

    def initTracePlot(self):
        '''
        Inits the station.plotItem title and the self.PlotCurveItem
        also connects the graph to self.pickPhase()
        '''
        self.station.plotItem.setTitle(self.tr.id)
        self.station.plotItem.titleLabel.setAttr('justify', 'left')
        self.station.plotItem.titleLabel.setMaximumHeight(0)
        self.station.plotItem.layout.setRowFixedHeight(0, 0)

        self.traceItem = pg.PlotCurveItem()
        self.traceItem.setClickable(True, width=50)
        self.traceItem.sigClicked.connect(self.pickPhase)

        self.station.plotItem.addItem(self.traceItem)

        self.plotTraceItem()
        self.plotPickItems()

    def pickPhase(self, evt):
        '''
        Evoked when the trace graph is clicked
        '''
        _thisPick = {'time':
                     self._pickTime(evt.pos()),
                     'amplitude':
                     self.traceItem.getData()[1][int(evt.pos().x())],
                     'station_id':
                     self.tr.id,
                     'station_lat':
                     self.station.getCoordinates()[0],
                     'station_lon':
                     self.station.getCoordinates()[1]}
        self.station.parent.parent.events.pickSignal(_thisPick)
        self.plotPickItems()

    def _pickTime(self, pos):
        '''
        Convinient function to get the time from pos :QtCore.Point:
        '''
        return self.tr.stats.starttime + pos.x() * self.tr.stats.delta


class Station(object):
    '''
    Represents a single Station and hold the plotItem in the layout
    '''
    def __init__(self, stream, parent):
        '''
        Object is initiated with a obspy Stream object and the parent mainDialog

        :stream: obspy.core.Stream()
        '''
        self.parent = parent
        self.plotItem = None

        self.st = stream.merge()
        self.stats = self.st[0].stats.copy()
        self.stats.channel = ''
        self.stats.channels = set([tr.stats.channel for tr in self.st])

        self._qTreeStationItem = QTreeWidgetItem()
        self._qTreeStationItem.setText(1, '%s.%s' %
                                      (self.stats.network,
                                       self.stats.station))
        self._qTreeStationItem.setText(2, '%.3f N, %.3f E' %
                                      (self.getCoordinates()[0],
                                       self.getCoordinates()[1]))

        self.channels = []
        for tr in self.st:
            self.channels.append(Channel(tr, station=self))

        self.setVisible(False)

    def setVisible(self, visible=True):
        '''
        Sets wheather the station is visible in the plot view
        '''
        basedir = os.path.dirname(__file__)

        self.visible = visible
        if visible:
            self._qTreeStationItem.setIcon(0,
                                           QIcon(os.path.join(basedir,
                                                 'icons/eye-24.png')))
            self.initPlot()
        else:
            self._qTreeStationItem.setIcon(0,
                                           QIcon(os.path.join(basedir,
                                                 'icons/eye-hidden-24.png')))
            self.delPlot()

    def initPlot(self):
        '''
        Inits the plot canvas pyqtgraph.plotItem
        '''
        self.plotItem = pg.PlotItem(name='%s.%s' %
                                    (self.stats.network, self.stats.station),
                                    clipToView=True, autoDownsample=True)
        self.plotItem.hideButtons()

        self.plotItem.setMouseEnabled(x=True, y=False)
        self.plotItem.getAxis('left').setWidth(35)
        self.plotItem.getAxis('bottom').setGrid(150)
        self.plotItem.enableAutoRange('y', 1.)

        self.plotItem.getAxis('bottom').setStyle(showValues=False)

        self.parent.GraphicsLayout.addItem(self.plotItem,
                                           row=self.parent.stations.index(self))
        self.parent.GraphicsLayout.nextRow()

        self.plotSelectedChannel()
        self.parent.updateAllPlots()

    def plotSelectedChannel(self):
        '''
        Plots the in the GUI selected channel
        '''
        for channel in self.channels:
            if channel.channel[-1] == self.parent.parent.visibleChannel:
                self.plotItem.clear()
                channel.initTracePlot()
                break

    def updateTraceFilter(self):
        '''
        Passes on the updated filter
        '''
        for channel in self.channels:
            if channel.channel[-1] == self.parent.parent.visibleChannel:
                channel.plotTraceItem()
                break

    def getPicks(self):
        '''
        Gets all the stations picks from parent.events
        '''
        self.picks = []
        for event in self.parent.parent.events:
            for pick in event.picks:
                if pick.station == self.stats.station and\
                   pick.network == self.stats.network:
                    self.picks.append(pick)
        return self.picks

    def delPlot(self):
        '''
        Delete the stations plot from layout
        '''
        try:
            self.parent.GraphicsLayout.removeItem(self.plotItem)
            self.plotItem = None
            self.parent.updateAllPlots()
        except:
            pass

    def getCoordinates(self):
        '''
        Return the coordinates from Station.stats

        ::return::
        :lat, lon: as Tuple
        '''
        try:
            return (self.stats.coordinates.latitude,
                    self.stats.coordinates.longitude)
        except:
            return (0.0, 0.0)


class Stations:
    '''
    Station() container object
    '''
    def __init__(self, st, parent):
        '''
        Inits with

        :parent: grapePicker QtGui.QMainWindow
        '''
        self.parent = parent
        self.GraphicsLayout = parent.qtGraphLayout

        self.stations = []
        for stat in set([tr.stats.station for tr in st]):
            self.addStation(st=st.select(station=stat))

    def addStation(self, st):
        '''
        Adds a station from

        :st: obspy stream
        '''
        self.stations.append(Station(stream=st, parent=self))
        self.parent.stationTree.addTopLevelItem(
            self.stations[-1]._qTreeStationItem)

    def visibleStations(self):
        '''
        Returns a list of all visible stations

        :return: list of Station()
        '''
        return [station for station in self.stations
                if station.visible]

    def updateAllPlots(self):
        '''
        Updates the plots, links the axis and clears the labeling
        '''
        visible_stations = self.visibleStations()
        for station in visible_stations:
            station.plotItem.setXLink(visible_stations[0].plotItem)
            station.plotItem.getAxis('bottom').setStyle(showValues=False)
        visible_stations[-1].plotItem.getAxis('bottom').setStyle(showValues=True)
            #except:
            #    pass

    def __iter__(self):
        return iter(self.stations)

    def __getitem__(self, index):
        return self.stations[index]

    def __len__(self):
        return len(self.stations)


class Pick:
    '''
    This object holds a pick, the correspoding QTreeWidgetItem and
    the pyqtgraph.InfiniteLine object
    '''
    def __init__(self, event, pickevt):
        '''
        Inits a Pick()
        :pickevt: Dictionary with keys
            ['station_id', 'station_lat', 'station_lon',
            'time', 'phase', 'amplitude']

        :event: parent Event() object
        '''
        self.event = event
        self.station_id = pickevt['station_id']
        self.station_lat = pickevt['station_lat']
        self.station_lon = pickevt['station_lon']
        self.time = pickevt['time']
        self.phase = pickevt['phase']
        self.amplitude = str(pickevt['amplitude'])

        self.pickItem = None

        self.network, self.station,\
            self.location, self.channel = self.station_id.split('.')

        self._QTreePickItem = QTreeWidgetItem()
        self._QTreePickItem.setText(1, '%s - %s\n%s'
                                    % (self.phase.name,
                                       self.station_id, self.time))

        self._QTreePickItem.setFont(1, QFont('', 8))
        self._QTreePickItem.setBackground(1, QBrush(self.phase.qcolor))
        self.event._QTreeEventItem.addChild(self._QTreePickItem)

    def getPickItem(self, channel):
        '''
        Function returns an pyqtgraph.InfiniteLine
        for plotting through Channel()
        '''
        self.channel = channel
        if self.pickItem is not None:
            return self.pickItem
        self.pickItem = pg.InfiniteLine()
        pos = (self.time - channel.tr.stats.starttime) / channel.tr.stats.delta
        self.pickItem.setValue(pos)
        self.pickItem.setPen(alpha=.8, color=self.phase.color)
        #self.pickItem.setMovable(True)
        #self.pickItem.setHoverPen(alpha=.3, width=10, color='w')
        return self.pickItem

    def asDict(self):
        '''
        Dictionary representation of the pick for exporting
        '''
        return {
            'station_id': self.station_id,
            'phase': self.phase.name,
            'time': str(self.time),
            'station_lat': self.station_lat,
            'station_lon': self.station_lon,
            'amplitude': self.amplitude
        }

    def __del__(self):
        self.event._QTreeEventItem.removeChild(self._QTreePickItem)
        self.pickItem.getViewBox().removeItem(self.pickItem)

class Event:
    '''
    Event container hold a list of the associated picks and a
    QTreeWidgetItem
    '''
    def __init__(self, parent, id):
        '''
        Inits the event with

        :id: integer
        :parent: parent Events() object
        '''
        self.parent = parent
        self.active = False
        self.id = id
        self.picks = []

        self._QTreeEventItem = QTreeWidgetItem()
        self._QTreeEventItem.setText(0, 'ID %d' % self.id)
        self._updateItemText()

    def addPickToEvent(self, pickevt):
        '''
        Adds a pick to the events
        '''
        self.picks.append(Pick(self, pickevt))
        self._updateItemText()
        return self.picks[-1]

    def setActive(self, active=True):
        '''
        Sets whether the event is the active pick event
        '''
        if active:
            self.active = True
            self._QTreeEventItem.setFont(0, QFont('', 10, QFont.Bold))
            self._QTreeEventItem.setFont(1, QFont('', 10, QFont.Bold))
        else:
            self.active = False
            self._QTreeEventItem.setFont(0, QFont('', 10, QFont.Normal))
            self._QTreeEventItem.setFont(1, QFont('', 10, QFont.Normal))
        return self

    def deletePick(self, pick):
        '''
        Deletes a Pick() from the event
        '''
        self.picks.remove(pick)
        pick.__del__()
        self._updateItemText()

    def getEventPicksAsDict(self):
        '''
        Returns a list of dictionaries Pick.asDict() of this Event()
        '''
        picks = []
        for pick in self.picks:
            picks.append(pick.asDict())
            picks[-1]['event_id'] = self.id
        return picks

    def _updateItemText(self):
        '''
        Updates the text of QTreeWidgetItem
        '''
        self._QTreeEventItem.setText(1, '%d Picks' % len(self.picks))

    def __del__(self):
        for pick in self.picks:
            pick.__del__()


class Events:
    '''
    Events container
    '''
    def __init__(self, parent):
        '''
        Inits the container
        :parent: parent grapePicker // QMainWindow
        '''
        self.parent = parent
        self.active_event = None
        self.events = []

    def addEvent(self, id=None):
        '''
        Adds event to the container with

        :id: Integer, if None it counts up
        '''
        if id is None:
            id = len(self.events)+1
        self.events.append(Event(parent=self, id=id))
        self.setActiveEvent(self.events[-1])
        self.parent.eventTree.addTopLevelItem(self.events[-1]._QTreeEventItem)

    def getEvent(self, id):
        '''
        :return: Event with id
        '''
        for event in self.events:
            if event.id == id:
                return event

    def setActiveEvent(self, event):
        '''
        :event: Event() is set the active Event
        '''
        self.active_event = event
        for ev in self.events:
            if ev == event:
                ev.setActive(True)
            else:
                ev.setActive(False)

    def pickSignal(self, pickevt):
        '''
        Called when a pick through the UI is done

        :pickevt: Dictionary with keys
            ['station_id', 'station_lat', 'station_lon',
            'time', 'phase', 'amplitude']
        '''
        pickevt['phase'] = self.parent.activePicker
        if self.active_event is None:
            return
        _p = self.active_event.addPickToEvent(pickevt)
        self.parent.eventTree.scrollToItem(_p._QTreePickItem)

    def deleteEvent(self, event):
        '''
        :event: Event() to be deleted from container object
        '''
        _id = self.parent.eventTree.indexOfTopLevelItem(event._QTreeEventItem)
        self.parent.eventTree.takeTopLevelItem(_id)
        self.events.remove(event)
        event.__del__()
        self.setActiveEvent(self.events[-1])

    '''
    File IO for the event class
    '''
    def exportJSON(self, filename):
        '''
        Export events as JSON file

        :filename: Filepath as string
        '''
        import json
        picks = [pick for event in self.events
                 for pick in event.getEventPicksAsDict()]
        with file(filename, 'w') as json_file:
            json.dump(picks, json_file, skipkeys=True, indent=0)

    def exportCSV(self, filename):
        '''
        Export events as CSV file

        :filename: Filepath as string
        '''
        import csv
        picks = [pick for event in self.events
                 for pick in event.getEventPicksAsDict()]
        if len(picks) == 0:
            return
        with file(filename, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=picks[0].keys())
            for pick in picks:
                writer.writerow(pick)

    def importJSON(self, filename):
        '''
        Import events from JSON file

        :filename: Filepath as string
        '''
        import json
        with file(filename, 'r') as json_file:
            events_json = json.load(json_file)
            for pick in events_json:
                try:
                    pick['phase'] = eval('pick%s()' % pick['phase'].upper())
                except:
                    raise ValueError('Could not import Phase %s in file %s'
                               % (pick['phase'], filename))
                pick['time'] = UTCDateTime(pick['time'])
                pick['amplitude'] = float(pick['amplitude'])
                pick['event_id'] = int(pick['event_id'])

        unique_events = set([pick['event_id'] for pick in events_json])
        for e in unique_events:
            self.addEvent(e)
        for pick in events_json:
            self.getEvent(pick['event_id']).addPickToEvent(pick)

    def __iter__(self):
        return iter(self.events)

    def __len__(self):
        return len(self.events)

'''
Different picks and their colors
'''
class pickP:
    def __init__(self):
        self.name = 'P'
        self.color = 'r'
        self.qcolor = QColor('red')
        self.qcolor.setAlpha(.4)


class pickS:
    def __init__(self):
        self.name = 'S'
        self.color = 'g'
        self.qcolor = QColor('green')
        self.qcolor.setAlpha(.4)


class pickAmp:
    def __init__(self):
        self.name = 'Amp'
        self.color = 'b'
        self.qcolor = QColor('blue')
        self.qcolor.setAlpha(.4)


class pick1:
    def __init__(self):
        self.name = '1'
        self.color = 'c'
        self.qcolor = QColor('yellow')
        self.qcolor.setAlpha(.4)


class pick2:
    def __init__(self):
        self.name = '2'
        self.color = 'w'
        self.qcolor = QColor('white')
        self.qcolor.setAlpha(.4)
