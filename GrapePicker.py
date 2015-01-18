import sys
from PySide.QtGui import *
from PySide.QtCore import *

import loadSGS as sgs
from guiContainer import *
import mainWindow

pickButtonMap = {
    'P': pickP(),
    'S': pickS(),
    'Amp': pickAmp(),
    '1': pick1(),
    '2': pick2()
}


class grapePicker(mainWindow.Ui_MainWindow, QMainWindow):
    def __init__(self, stream=None, nplots=5, parent=None):
        '''
        Init the Application and set up the GUI
        '''
        # Initialising Qt
        QLocale.setDefault(QLocale.c())
        app = QApplication(sys.argv)

        # Setting up and loading UI
        super(grapePicker, self).__init__(parent)
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

        print 'HERE!'
        # Executing Qt
        self.show()
        app.exec_()

    def closeEvent(self, event):
        '''
        Save backup of active picks
        '''
        self.events.exportJSON('.~grapePicker.bak.json')

    def _initStationTree(self):
        '''
        Setup stationtree :QTreeWidgetItem:
        '''
        self.stationTree.setColumnCount(3)
        self.stationTree.setColumnWidth(0, 60)
        self.stationTree.setColumnWidth(1, 90)
        self.stationTree.setColumnWidth(2, 150)
        self.stationTree.setExpandsOnDoubleClick(False)
        self.stationTree.itemDoubleClicked.connect(self._changeStationVisibility)

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
            if station._qTreeStationItem.isSelected():
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

    def _initEventTree(self):
        '''
        Init the event tree :QTreeWidgetItem:
        '''
        self.eventTree.setColumnCount(2)
        self.eventTree.setColumnWidth(0, 80)
        #self.eventTree.itemClicked.connect()

    def _connectFileMenu(self):
        '''
        Connect File QMenu
        '''
        self.actionAs_JSON.triggered.connect(self._picksSaveJSON)
        self.actionAs_CSV.triggered.connect(self._picksSaveCSV)
        self.actionLoad_JSON.triggered.connect(self._picksLoadJSON)

    def _picksSaveCSV(self):
        '''
        Open file dialog and save CSV
        '''
        fileDialog = QFileDialog.getSaveFileName(self, 'Save CSV',
                                                 filter='CSV File (*.csv)')
        filename = fileDialog.getSaveFileName()

        if filename[0] is not u'':
            self.events.exportCSV(filename[0])

    def _picksSaveJSON(self):
        '''
        Open file dialog and save JSON
        '''
        filename = QFileDialog.getSaveFileName(self, 'Save JSON',
                                               filter='JSON File (*.json)')
        if filename[0] is not u'':
            self.events.exportJSON(filename[0])

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
        self.addEventBtn.clicked.connect(self.events.addEvent)
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
            if event._QTreeEventItem.isSelected():
                self.events.deleteEvent(event)
                continue
            for pick in event.picks:
                if pick._QTreePickItem.isSelected():
                    event.deletePick(pick)
                    continue

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
            self.filterArgs = None
            self.filterButton.setText('Filter On')
        for station in self.stations:
            if station.visible:
                station.updateTraceFilter()
        print self.filterArgs

grapePicker(stream=sgs.events[1].Stream())