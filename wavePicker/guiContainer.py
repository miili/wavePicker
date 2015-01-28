from PySide.QtGui import *
from PySide.QtCore import *

from obspy.core import UTCDateTime, Stream, AttribDict

import pyqtgraph as pg

import os, sip

class Channel(object):
    '''
    Channel Container Object handels an individual channel

    self.QChannelItem represents the QTreeWidgetItem
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

        self.QChannelItem = QTreeWidgetItem()
        self.QChannelItem.setText(1, '%s @ %d Hz' %
                                         (self.tr.stats.channel,
                                          1./self.tr.stats.delta))
        self.QChannelItem.setText(2, '%s\n%s' %
                                         (self.tr.stats.starttime,
                                          self.tr.stats.endtime))
        self.QChannelItem.setFont(1, QFont('', 7))
        self.QChannelItem.setFont(2, QFont('', 7))
        self.station.QStationItem.addChild(self.QChannelItem)

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
                self.station.plotItem.addItem(pick.getPickLineItem(self))

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
        self.stats.channel = None
        self.channels = set([tr.stats.channel for tr in self.st])

        self.QStationItem = QTreeWidgetItem()
        self.QStationItem.setText(1, '%s.%s' %
                                      (self.stats.network,
                                       self.stats.station))
        #self.QStationItem.setText(2, '%.3f N, %.3f E' %
        #                              (self.getCoordinates()[0],
        #                               self.getCoordinates()[1]))

        self.picks = []
        self.station_events = []

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
            self.QStationItem.setIcon(0,
                                           QIcon(os.path.join(basedir,
                                                 'icons/eye-24.png')))
            self.initPlot()
        else:
            self.QStationItem.setIcon(0,
                                           QIcon(os.path.join(basedir,
                                                 'icons/eye-hidden-24.png')))
            self.delPlot()

    def initPlot(self):
        '''
        Inits the plot canvas pyqtgraph.plotItem
        '''
        if not self.visible:
            return
        self.plotItem = pg.PlotItem(name='%s.%s' %
                                    (self.stats.network, self.stats.station),
                                    clipToView=True, autoDownsample=True)
        self.plotItem.hideButtons()

        self.plotItem.setMouseEnabled(x=True, y=False)
        self.plotItem.getAxis('left').setWidth(35)
        self.plotItem.getAxis('bottom').setGrid(150)
        self.plotItem.enableAutoRange('y', 1.)

        self.plotItem.getAxis('bottom').setStyle(showValues=False)

        self.plotSelectedChannel()
        self.parent.GraphicsLayout.addItem(self.plotItem,
                                           row=self.parent.stations.index(self))

        self.parent.GraphicsLayout.nextRow()
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
            for pick in self.getPicks():
                pick.pickLineItem = None

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

    def getHypStaString(self):
        '''
        returns the station's Hypoinverse Station String in data format #1

        Hypoinverse Documentation P. 28
        '''
        hyp_sta = {
            'station_name': self.stats.station,
            'station_network': self.stats.network,
            'station_location': self.stats.location,
            'station_channel_code': '',
            'station_lat': self.getCoordinates()[0],
            'station_lon': self.getCoordinates()[1],
            'station_elevation': self.stats.coordinates.get('elevation', 0.0),

            'station_weight': 'f',  # Full weight
            'default_period': 2,
            'station_component_code': ' ',  # Optional
            'use_alternate_crust_model': False,  # Optional
            'station_remark': None,  # Optional
            'P_delay_set1': 0,  # P delay in sec for set 1
            'P_delay_set2': 0,  # P delay in sec for set 2
            'amplitude_correction': 0,
            'amplitude_weight': ' ',
            'duration_magnitude_correction': 0,
            'duration_magnitude_weight': '',
            'instrument_type_code': 0,
            'calibration_factor': 0,
            'alternate_component_code': '',
            'mark_negative_depth': ''
        }
        # Station Name
        rstr = '%5s ' % hyp_sta['station_name']
        # Seismic Network Code
        rstr += '%2s ' % hyp_sta.get('station_network', '')
        # Station Component Code
        rstr += '%1s' % hyp_sta.get('station_component_code', '')
        # Channel code
        rstr += '%3s ' % hyp_sta.get('station_channel_code', '')
        # Station Weight
        rstr += '%1s' % str(hyp_sta.get('station_weight', 'f'))
        # Latitude in deg/min
        rstr += '%2d %7.4f%s' % (int(abs(hyp_sta['station_lat'])),
                               ((abs(hyp_sta['station_lat']) % 1) * 60),
                                'N' if hyp_sta['station_lat'] > 0 else 'S')
        # Longitude in deg/min
        rstr += '%3d %7.4f%s' % (int(abs(hyp_sta['station_lon'])),
                               ((abs(hyp_sta['station_lon']) % 1) * 60),
                                'E' if hyp_sta['station_lon'] > 0 else 'W')
        # Station elevation
        rstr += '%4d' % hyp_sta.get('station_elevation', 0)
        # Default period in sec
        rstr += '%3.1f  ' % hyp_sta.get('default_period', 2)
        # Alternate Crust model
        rstr += '%1s' % ('A' if hyp_sta.get('use_alternate_crust_model', False)
                         else '')
        # Station Remark
        rstr += '%1s' % ('' if hyp_sta.get('station_remark', None) is None
                         else hyp_sta['station_remark'])
        # P Delays
        rstr += '%5.2f ' % hyp_sta.get('P_delay_set1', 0)
        rstr += '%5.2f ' % hyp_sta.get('P_delay_set1', 0)
        # Amplitude correction
        rstr += '%5.2f' % hyp_sta.get('amplitude_correction', 1)
        # Amplitude weight
        rstr += '%1s' % hyp_sta.get('amplitude_weight', '')
        # Duration magnitude correction
        rstr += '%5.2f' % hyp_sta.get('duration_magnitude_correction', 0)
        # Duration magnitude weight code
        rstr += '%1s' % hyp_sta.get('duration_magnitude_weight', '')
        # Instrument type code
        rstr += '%1d' % hyp_sta.get('instrument_type_code', 0)
        # Calibration Factor
        rstr += '%6.2f' % hyp_sta.get('calibration_factor', 1.4)
        # Location code
        rstr += '%2s' % hyp_sta.get('station_location', '')
        # Alternate component code
        rstr += '%3s' % hyp_sta.get('alternate_component_code', '')
        # Mark negative depth
        rstr += '%1s' % hyp_sta.get('mark_negative_depth', '')
        print rstr
        print len(rstr)+1
        return rstr

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
        self.stream = st

        self.stations = []
        for stat in set([tr.stats.station for tr in st]):
            self.addStation(st=st.select(station=stat))

        self.sorted_by = None
        self.sortableAttribs()

    def addStation(self, st):
        '''
        Adds a station from

        :st: obspy stream
        '''
        self.stations.append(Station(stream=st, parent=self))
        self.parent.stationTree.addTopLevelItem(
            self.stations[-1].QStationItem)

    def visibleStations(self):
        '''
        Returns a list of all visible stations

        :return: list of Station()
        '''
        return [station for station in self.stations
                if station.visible]

    def sortableAttribs(self):
        ignore_attribs = ['channel', 'mseed', 'SAC', 'sampling_rate',
                          '_format', 'delta', 'calib']
        self.sortable_attribs = {}
        attribs = set.intersection(*(set(station.stats.keys())
                                     for station in self.stations))
        for key in attribs:
            if key in ignore_attribs:
                continue
            self.sortable_attribs[key] = True
            if isinstance(eval('self.stations[0].stats.%s' % key), AttribDict):
                self.sortable_attribs[key] = {}
                subkeys = set(['%s.%s' % (key, subkey) for tr in self.stream
                               for subkey in eval('tr.stats.%s.keys()' % key)])
                for skey in subkeys:
                    self.sortable_attribs[key][skey] = True

    def sortByAttrib(self, key):
        '''
        Sort station by attribute key
        '''
        from operator import attrgetter
        self.stations = sorted(self.stations, key=attrgetter('stats.%s' % key))
        self.sorted_by = key

        self._sortStationsOnGUI()

    def _sortStationsOnGUI(self):
        '''
        Sort the stations on QTreeWidget and GraphicsLayout
        '''
        # Clear all plots
        self.parent.qtGraphLayout.clear()
        # Update QtreeWidget
        for station in self.stations:
            self.parent.stationTree.takeTopLevelItem(self.parent.stationTree.indexOfTopLevelItem(station.QStationItem))
        for station in self.stations:
            self.parent.stationTree.addTopLevelItem(station.QStationItem)
            station.initPlot()
        self.updateAllPlots()

    def showSortQMenu(self, pos):
        '''
        Sort Menu for the QTreeWidget
        '''
        sort_menu = QMenu()
        sort_menu.setFont(QFont('', 9))
        _t = sort_menu.addAction('Sort by attribute')
        _t.setEnabled(False)
        _t.setFont(QFont('', 8, QFont.Bold))
        for attrib, subattrib in self.sortable_attribs.items():
            if isinstance(subattrib, bool):
                self._addActionSortMenu(attrib, sort_menu)
            else:
                _submenu = sort_menu.addMenu(attrib)
                for sattrib in subattrib.keys():
                    self._addActionSortMenu(sattrib, _submenu)
        sort_menu.exec_(self.parent.stationTree.mapToGlobal(pos))

    def _addActionSortMenu(self, attrib, menu):
        '''
        Help function for self.showSortQMenu
        '''
        _action = menu.addAction(attrib)
        _action.setCheckable(True)
        _action.triggered.connect(lambda: self.sortByAttrib(attrib))
        if attrib == self.sorted_by:
            _action.setChecked(True)
        else:
            _action.setChecked(False)

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

    def exportHypStaFile(self, filename):
        with open(filename, 'w') as stat_file:
            for station in self.stations:
                stat_file.write(station.getHypStaString() + '\n')

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

        self.pickLineItem = None
        self.pickHighlighted = False

        self.network, self.station,\
            self.location, self.channel = self.station_id.split('.')

        self.QPickItem = QTreeWidgetItem()
        self.QPickItem.setText(1, '%s - %s\n%s'
                                    % (self.phase.name,
                                       self.station_id, self.time))

        self.QPickItem.setFont(1, QFont('', 8))
        self.QPickItem.setBackground(1, QBrush(self.phase.qcolor))
        #self.event.QEventItem.addChild(self.QPickItem)
        self.event.getStationItem(self.station).addChild(self.QPickItem)

    def getPickLineItem(self, channel):
        '''
        Function returns an pyqtgraph.InfiniteLine
        for plotting through Channel()
        '''
        self.channel = channel
        if self.pickLineItem is not None:
            return self.pickLineItem
        self.pickLineItem = pg.InfiniteLine()
        pos = (self.time - channel.tr.stats.starttime) / channel.tr.stats.delta
        self.pickLineItem.setValue(pos)
        self.pickLineItem.setPen(color=self.phase.color, width=1)
        #self.pickLineItem.setMovable(True)
        #self.pickLineItem.setHoverPen(alpha=.3, width=10, color='w')
        return self.pickLineItem

    def highlightPickLineItem(self):
        if self.pickLineItem is None:
            return False
        if self.pickHighlighted:
            self.pickLineItem.setPen(color=self.phase.color, width=1)
            self.pickHighlighted = False
            self.QPickItem.setFont(1, QFont('', 8, QFont.Normal))
        else:
            self.pickLineItem.setPen(color=self.phase.color, width=3)
            self.pickHighlighted = True
            self.QPickItem.setFont(1, QFont('', 8, QFont.Bold))

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

    def stringHypoinverse(self):
        '''
        Returns the Hypoinverse2000 phase file for this pick
        '''
        pass

    def __del__(self):
        self.event.getStationItem(self.station).removeChild(self.QPickItem)
        self.pickLineItem.getViewBox().removeItem(self.pickLineItem)
        self.pickLineItem = None


class Event:
    '''
    Event container holds a list of the associated picks and a
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

        self.QEventItem = QTreeWidgetItem()
        self.QEventItem.setText(0, 'Ev %d' % self.id)
        self._initQStationItems()
        self._updateItemText()

    def _initQStationItems(self):
        self.QStationEventItems = {}
        for station in [station.stats.station for
                        station in self.parent.parent.stations]:
            self.QStationEventItems[station] = QTreeWidgetItem()
            self.QStationEventItems[station].setText(0, station)
            self.QStationEventItems[station].setHidden(True)
            self.QEventItem.addChild(self.QStationEventItems[station])

    def getStationItem(self, station):
        if self.QStationEventItems.has_key(station):
            return self.QStationEventItems.get(station)
        else:
            self.QStationEventItems[station] = QTreeWidgetItem()
            self.QEventItem.addChild(self.QStationEventItems[station])
            self.QStationEventItems[station].setHidden(True)
            return self.QStationEventItems.get(station)

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
            self.QEventItem.setFont(0, QFont('', 10, QFont.Bold))
            self.QEventItem.setFont(1, QFont('', 10, QFont.Bold))
        else:
            self.active = False
            self.QEventItem.setFont(0, QFont('', 10, QFont.Normal))
            self.QEventItem.setFont(1, QFont('', 10, QFont.Normal))
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

    def _getPickedStations(self):
        return [pick.station for pick in self.picks]

    def _getPicksForStation(self, station):
        return [pick for pick in self.picks if pick.station is station]

    def _updateQStationEventItems(self):
        '''
        Updates the Event Stations QTreeWidgetItems
        '''
        picked_stations = self._getPickedStations()
        for station, item in self.QStationEventItems.iteritems():
            npicks = picked_stations.count(station)
            p_text = ('Pick' if  npicks == 1 else 'Picks')
            item.setText(1, '%d %s' % (npicks, p_text))
            if station in picked_stations:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _updateItemText(self):
        '''
        Updates the text of QTreeWidgetItem
        '''
        self.QEventItem.setText(1, '%d Stations'
                                     % len(set([pick.station for
                                                pick in self.picks])))
        self._updateQStationEventItems()

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
        self.parent.eventTree.addTopLevelItem(self.events[-1].QEventItem)

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

    def deleteEvent(self, event):
        '''
        :event: Event() to be deleted from container object
        '''
        _id = self.parent.eventTree.indexOfTopLevelItem(event.QEventItem)
        self.parent.eventTree.takeTopLevelItem(_id)
        self.events.remove(event)
        event.__del__()
        self.setActiveEvent(self.events[-1])

    def getAllPicks(self):
        return [pick for event in self.events for pick in event.picks]

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
        self.parent.eventTree.scrollToItem(_p.QPickItem)

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

