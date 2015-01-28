import sys
from PySide.QtGui import *
from PySide.QtCore import *

from guiContainer import *
import mainWindow

pickButtonMap = {
    'P': pickP(),
    'S': pickS(),
    'Amp': pickAmp(),
    '1': pick1(),
    '2': pick2()
}


class wavePicker(mainWindow.Ui_MainWindow, QMainWindow):
    def __init__(self, stream=None, nplots=5,
                 project_name='Untitled', parent=None):
        '''
        A Seismic Wave Time Arrival Picker for ObsPy Stream Objects

        https://github.com/miili/wavePicker

        :param stream: Stream object, type obspy.core.Stream
        :param nplots: Number of plots to initialise, type int (default: 5)
        :param project_name: Project name, type string (default: 'Untitled')
        '''
        # Initialising Qt
        QLocale.setDefault(QLocale.c())
        app = QApplication(sys.argv)

        # Setting up and loading UI
        super(wavePicker, self).__init__(parent)
        self.setupUi(self)

        if stream is None or not isinstance(stream, Stream):
            raise AttributeError('Define stream as obspy.core.Stream object')
        self.stream = stream

        '''
        GUI init parameters
        '''
        self.nplots = nplots               # init gui with 5 traces
        self.visibleChannel = 'Z'     # init with channel z
        self.activePicker = pickP()   # init with P picker
        self.project_name = project_name

        self.setWindowTitle('wavePicker - %s' % self.project_name)

        '''
        Init internal objects
        '''
        self.events = Events(self)  # init event class
        self.filterArgs = None      # start with blank filter
        # init stations from self.stream
        self.stations = Stations(self.stream, self)

        '''
        Set GUI parameters and setup connections
        '''
        self.qtGraphLayout.ci.layout.setVerticalSpacing(0)

        self._initEventTree()

        self._connectFileMenu()

        self._initStationTree()

        self._connectPickButtons()
        self._connectStationButtons()
        self._ConnectFilterSliders()

        for i, sta in enumerate(self.stations):
            if i < self.nplots:
                sta.setVisible(True)
        # Executing Qt
        self.show()
        app.exec_()

    def closeEvent(self, event):
        '''
        Save backup of active picks
        '''
        self.events.exportJSON('.~wavePicker.bak.json')

    def _initStationTree(self):
        '''
        Setup stationtree :QTreeWidgetItem:
        '''
        self.stationTree.setColumnCount(3)
        self.stationTree.setColumnWidth(0, 40)
        self.stationTree.setColumnWidth(1, 90)
        self.stationTree.setColumnWidth(2, 150)
        self.stationTree.setExpandsOnDoubleClick(False)
        self.stationTree.itemDoubleClicked.connect(self._changeStationVisibility)

        self.stationTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stationTree.customContextMenuRequested.connect(self.stations.showSortQMenu)

    def _connectStationButtons(self):
        '''
        Setup Station Buttons - Select visible channel
        '''
        self.compZbtn.clicked.connect(self._changeSelectedChannel)
        self.compEbtn.clicked.connect(self._changeSelectedChannel)
        self.compNbtn.clicked.connect(self._changeSelectedChannel)

    def _changeStationVisibility(self, item):
        '''
        Change selected stations visibility
        '''
        for station in self.stations:
            if station.QStationItem.isSelected():
                station.setVisible(not station.visible)

    def _changeSelectedChannel(self):
        '''
        Change plotted channel
        '''
        for btn in [self.compEbtn, self.compNbtn, self.compZbtn]:
            if btn.isChecked():
                self.visibleChannel = btn.text()
        for station in self.stations:
            if station.visible:
                station.plotSelectedChannel()

    '''
    Event Tree Frunctions
    '''
    def _initEventTree(self):
        '''
        Init the event tree :QTreeWidgetItem:
        '''
        self.eventTree.setColumnCount(2)
        self.eventTree.setColumnWidth(0, 100)
        self.eventTree.itemDoubleClicked.connect(self._highlightPick)
        #self.eventTree.itemClicked.connect()

    def _highlightPick(self):
        picks = self.events.getAllPicks()
        for pick in picks:
            if pick.QPickItem.isSelected():
                pick.highlightPickLineItem()

    def _connectFileMenu(self):
        '''
        Connect File QMenu
        '''
        self.actionAs_JSON.triggered.connect(self._picksSaveJSON)
        self.actionLoad_JSON.triggered.connect(self._picksLoadJSON)
        self.actionExport_CSV.triggered.connect(self._picksExportCSV)
        self.actionExport_stat.triggered.connect(self._stationsExportSta)
        self.actionExport_phs.triggered.connect(self._eventsExportPhs)

    def _picksSaveJSON(self):
        '''
        Open file dialog and save JSON
        '''
        filename = QFileDialog.getSaveFileName(self, 'Save JSON',
                                               self.project_name,
                                               filter='JSON File (*.json)')[0]
        if filename is not u'':
            if filename[-5:].lower() != '.json':
                filename += '.json'
            self.events.exportJSON(filename)

    def _picksLoadJSON(self):
        '''
        Open file dialog and load JSON
        '''
        filename = QFileDialog.getOpenFileName(self, 'Import JSON',
                                               filter='JSON File (*.json)',
                                               options=QFileDialog.ReadOnly,
                                               filemode=QFileDialog.ExistingFile)
        if filename[0] is not u'':
            self.events.importJSON(filename[0])
            self._changeSelectedChannel()

    def _picksExportCSV(self):
        '''
        Open file dialog and save CSV
        '''
        filename = QFileDialog.getSaveFileName(self, 'Save CSV', self.project_name + '.csv',
                                                 filter='CSV File (*.csv)')[0]
        if filename is not u'':
            if filename[-4:].lower() != '.csv':
                filename += '.csv'
            self.events.exportCSV(filename)

    def _stationsExportSta(self):
        '''
        Open file dialog and save Hypoinverse Stat file
        '''
        filename = QFileDialog.getSaveFileName(self,'Save Hypoinverse2000 Station File',
                                               self.project_name + '.sta',
                                               filter='STA File (*.sta)')[0]
        if filename is not u'':
            if filename[-4:].lower() != '.sta':
                filename += '.sta'
            self.stations.exportHypStaFile(filename)

    def _eventsExportPhs(self):
        '''
        Open file dialog and save Hypoinverse Stat file
        '''
        filename = QFileDialog.getSaveFileName(self,'Save Hypoinverse2000 Phase File',
                                               self.project_name + '.phs',
                                               filter='PHS File (*.phs)')[0]
        if filename is not u'':
            if filename[-4:].lower() != '.phs':
                filename += '.phs'
            self.events.exportAllEventsPhases(filename)

    '''
    Picking Functions
    '''
    def _changeActivePicker(self):
        '''
        Called when the active picker changes
        '''
        for btn in [self.pickS, self.pickP,
                    self.pickAmp, self.pick1, self.pick2]:
            if btn.isChecked():
                self.activePicker = pickButtonMap[btn.text()]

    def _connectPickButtons(self):
        '''
        Connect the pick buttons
        '''
        self.addEventBtn.clicked.connect(self._addEventDialog)
        self.deleteItemBtn.clicked.connect(self._deleteButtonClick)
        self.pick1.clicked.connect(self._changeActivePicker)
        self.pick2.clicked.connect(self._changeActivePicker)
        self.pickP.clicked.connect(self._changeActivePicker)
        self.pickS.clicked.connect(self._changeActivePicker)
        self.pickAmp.clicked.connect(self._changeActivePicker)

    def _deleteButtonClick(self):
        '''
        Called when the delete Item button is triggered
        '''
        for event in self.events:
            if event.QEventItem.isSelected():
                self.events.deleteEvent(event)
                continue
            for pick in event.picks:
                if pick.QPickItem.isSelected():
                    event.deletePick(pick)
                    continue

    def _addEventDialog(self):
        init_id = (max([event.id for event in self.events])+1
                   if len(self.events) > 0 else 0)
        event_id = QInputDialog.getInteger(self, 'New Event ID', 'Event ID',
                                           minValue=0, step=1,
                                           value=init_id)
        if event_id[1]:
            self.events.addEvent(id=event_id[0])

    '''
    Bandpass Filter Functions
    '''
    def _ConnectFilterSliders(self):
        '''
        Connect QSlider s and QSpinBox s
        '''
        self.fmaxSpin.valueChanged.connect(self._spinMaxChanged)
        self.fminSpin.valueChanged.connect(self._spinMinChanged)
        self.fmaxSlider.valueChanged.connect(self._sliderMaxChanged)
        self.fminSlider.valueChanged.connect(self._sliderMinChanged)
        self.cornersSpin.valueChanged.connect(self._updateFilterArgs)
        self.zerophaseCheck.stateChanged.connect(self._updateFilterArgs)
        self.filterButton.clicked.connect(self._updateFilterArgs)

    def _spinMaxChanged(self):
        '''
        Called when QSpinBox fmax is changed
        '''
        self.fmaxSlider.setValue(int(self.fmaxSpin.value()*10))
        if self.fmaxSpin.value() <= self.fminSpin.value():
            self.fminSpin.setValue(self.fmaxSpin.value()-1.)
        self._updateFilterArgs()

    def _spinMinChanged(self):
        '''
        Called when QSpinBox fmin is changed
        '''
        self.fminSlider.setValue(int(self.fminSpin.value()*10))
        if self.fminSpin.value() >= self.fmaxSpin.value():
            self.fmaxSpin.setValue(self.fminSpin.value()+1.)
        self._updateFilterArgs()

    def _sliderMaxChanged(self):
        '''
        Called when QSlider fmax is changed
        '''
        self.fmaxSpin.setValue(float(self.fmaxSlider.value()/10))

    def _sliderMinChanged(self):
        '''
        Called when QSlider fmin is changed
        '''
        self.fminSpin.setValue(float(self.fminSlider.value()/10))

    def _updateFilterArgs(self):
        '''
        Called by _spinMaxChanged() and _spinMinChanged() to change
        the filter parameters in self.filterArgs
        '''
        if self.filterButton.isChecked():
            self.filterArgs = {
                'freqmin': self.fminSpin.value(),
                'freqmax': self.fmaxSpin.value(),
                'corners': self.cornersSpin.value(),
                'zerophase': self.zerophaseCheck.isChecked()
            }
            self.filterButton.setText('Filter Off')
        else:
            if self.filterArgs is None:
                return
            self.filterArgs = None
            self.filterButton.setText('Filter On')
        for station in self.stations:
            if station.visible:
                station.updateTraceFilter()
