import base64
from Crypto.Cipher import AES
import datetime
from datetime import date, timedelta
import dropbox
from dropbox import rest as dbrest
import logging
import operator
import os.path
import re
import sys
import tempfile
import time
from time import gmtime, strftime
import urllib3
import requests
from requests.adapters import HTTPAdapter
import webbrowser
from gmusicapi import Mobileclient
from gmusicapi import Musicmanager
from gmusicapi.exceptions import AlreadyLoggedIn
from PySide import QtGui
from PySide import QtCore
from PySide.QtCore import *
from PySide.QtGui import *

# To Do
#
# See if you can make reorder playlist work. Drag and drop doesn't work correctly

# Changes
#

# Change this to your email address and your password. If you use 2 factor authentication you need to generate an app password.
#
# To generate an App Password:
# Log into Google
# Click on the Blue circle with a person in it in the top right corner of the browser
# Click on Account
# Click on the Security tab
# Click on the Settings link next to App Passwords.
# Generate an App Password. I clicked on the Select app drop down and chose Other (Custom name) and entered GMusic Python as the name then click on generate.

username = "myusername@gmail.com"
password = "mypassword"

tableForegroundColor = None

tableBackgroundColor = None

# Change this to True if you want to allow duplicate playlist names (not recommended because it can cause problems)
AllowDuplicatePlaylistNames = False

### DO NOT EDIT ANYTHING BELOW THIS LINE
urllib3.disable_warnings()

# Fix for the error NotImplementedError: resource_filename() only supported for .egg, not .zip which is related to Dropbox API
# http://mfctips.com/2013/05/03/dropbox-python-sdk-with-py2exe-causes-notimplementederror-resource_filename-only-supported-for-egg-not-zip/

# This is an SSL patch found at http://stackoverflow.com/questions/24973326/requests-exceptions-sslerror-errno-185090050 to force this script to use the local cacert.pem. This is needed when compiling this script into an exe using py2exe or the executable will throw an SSL error
def _SSL_patch_requests():
    orig_send = HTTPAdapter.send
    def _send_no_verify(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        return orig_send(self, request, stream, timeout, os.getcwd() + '\\cacert.pem' if verify else False, cert, proxies)
    HTTPAdapter.send = _send_no_verify

# When we are running the exe, we need to load the SSL cert
if sys.argv[0].find(".exe") != -1:
     _SSL_patch_requests()

class TableModel(QAbstractTableModel):
    def flags(self, index):
        if index.isValid():
              return Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
              return Qt.ItemIsDropEnabled | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def __init__(self, parent, mylist, header, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = mylist
        self.header = header
    def moveRows(self, parent, source_first, source_last, parent2, dest):
        print "moveRows called, self.data = %s" % self.data
        self.beginMoveRows(parent, source_first, source_last, parent2, dest)

        self.data = self.data[1] + self.data[0] + self.data[2]
        self.endMoveRows()
        print "moveRows finished, self.data = %s" % self.data
    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.mylist[0])
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.mylist = sorted(self.mylist, key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.emit(SIGNAL("layoutChanged()"))

    def dragMoveEvent(self, event):
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()

        '''
        def moveRows(self, parent, source_first, source_last, parent2, dest):
        print "moveRows called, self.data = %s" % self.data
        self.beginMoveRows(parent, source_first, source_last, parent2, dest)

        self.data = self.data[1] + self.data[0] + self.data[2]
        self.endMoveRows()
        print "moveRows finished, self.data = %s" % self.data
        '''

class TableView(QTableView):
    def __init__(self, parent=None):
        QTableView.__init__(self, parent=None)
        self.setSelectionMode(self.ExtendedSelection)
        self.setDragEnabled(True)
        self.acceptDrops()
        self.setDragDropMode(self.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)

    def dropEvent(self, event):
        if event.source() == self and (event.dropAction() == Qt.MoveAction or self.dragDropMode() == QAbstractItemView.InternalMove):
            success, row, col, topIndex = self.dropOn(event)
            if success:
                selRows = self.getSelectedRowsFast()

                top = selRows[0]
                # print 'top is %d'%top
                dropRow = row
                if dropRow == -1:
                    dropRow = self.rowCount()
                # print 'dropRow is %d'%dropRow
                offset = dropRow - top
                # print 'offset is %d'%offset

                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0
                    self.insertRow(r)
                    # print 'inserting row at %d'%r


                selRows = self.getSelectedRowsFast()
                # print 'selected rows: %s'%selRows

                top = selRows[0]
                # print 'top is %d'%top
                offset = dropRow - top
                # print 'offset is %d'%offset
                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0

                    for j in range(self.columnCount()):
                        # print 'source is (%d, %d)'%(row, j)
                        # print 'item text: %s'%self.item(row,j).text()
                        source = QTableWidgetItem(self.item(row, j))
                        # print 'dest is (%d, %d)'%(r,j)
                        self.setItem(r, j, source)

                # Why does this NOT need to be here?
                # for row in reversed(selRows):
                    # self.removeRow(row)

                event.accept()

        else:
            QTableView.dropEvent(event)
    '''
    def getSelectedRowsFast(self):
        print "in getSelectedRowsFast()"
        selRows=[]
        
        for item in self.selectedIndexes():
             if item.row() not in selRows:
                  print "adding to selRows"
                  selRows.append(item.row())
        return selRows
        #selRows = []
        #for item in self.selectedItems():
        #    if item.row() not in selRows:
        #        selRows.append(item.row())
        #return selRows

    def droppingOnItself(self, event, index):
        print "in droppingOnItself()"
        dropAction = event.dropAction()

        if self.dragDropMode() == QAbstractItemView.InternalMove:
            dropAction = Qt.MoveAction

        if event.source() == self and event.possibleActions() & Qt.MoveAction and dropAction == Qt.MoveAction:
            selectedIndexes = self.selectedIndexes()
            child = index
            while child.isValid() and child != self.rootIndex():
                if child in selectedIndexes:
                    return True
                child = child.parent()

        return False

    def dropOn(self, event):
        print "in dropOn()"
        if event.isAccepted():
            return False, None, None, None

        index = QModelIndex()
        row = -1
        col = -1

        if self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(event.pos()):
                index = self.rootIndex()

        if self.model().supportedDropActions() & event.dropAction():
            if index != self.rootIndex():
                dropIndicatorPosition = self.position(event.pos(), self.visualRect(index), index)

                if dropIndicatorPosition == QAbstractItemView.AboveItem:
                    row = index.row()
                    col = index.column()
                    # index = index.parent()
                elif dropIndicatorPosition == QAbstractItemView.BelowItem:
                    row = index.row() + 1
                    col = index.column()
                    # index = index.parent()
                else:
                    row = index.row()
                    col = index.column()

            if not self.droppingOnItself(event, index):
                # print 'row is %d'%row
                # print 'col is %d'%col
                return True, row, col, index

        return False, None, None, None

    def position(self, pos, rect, index):
        print "in position()"
        r = QAbstractItemView.OnViewport
        margin = 2
        if pos.y() - rect.top() < margin:
            r = QAbstractItemView.AboveItem
        elif rect.bottom() - pos.y() < margin:
            r = QAbstractItemView.BelowItem 
        elif rect.contains(pos, True):
            r = QAbstractItemView.OnItem

        if r == QAbstractItemView.OnItem and not (self.model().flags(index) & Qt.ItemIsDropEnabled):
            r = QAbstractItemView.AboveItem if pos.y() < rect.center().y() else QAbstractItemView.BelowItem

        return r
    
    def dragEnterEvent(self, event):
        print "in dragEnterEvent()"
        event.accept()
    '''
    def dragMoveEvent(self, event):
        event.accept()

    '''
    def dropEvent(self, event):
        print "dropEvent called"
        point = event.pos()
        self.model().moveRows(QModelIndex(), 0, 0, QModelIndex(), 1)
        event.accept()
    '''

    def mousePressEvent(self, event):
        self.startDrag(event)

    def startDrag(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return

        # self.moved_data = self.model().data[index.row()]

        drag = QDrag(self)

        mimeData = QMimeData()
        mimeData.setData("application/blabla", "")
        drag.setMimeData(mimeData)

        pixmap = QPixmap()
        pixmap = pixmap.grabWidget(self, self.visualRect(index))
        drag.setPixmap(pixmap)

        result = drag.start(Qt.MoveAction)

class TableSwitcher(QtGui.QTableWidget):
    def dropEvent(self, dropEvent):
    
        item_src = self.selectedItems()[0]
        item_dest = self.itemAt(dropEvent.pos())

        if item_src is None or item_dest is None or (item_src is not None and item_src.text() != "" and item_dest is not None and item_dest.text() != ""):
             dropEvent.ignore()
             return

        src_row = item_src.row()
        src_col = item_src.column()

        dest_value = item_dest.text()
        
        super(TableSwitcher, self).dropEvent(dropEvent)
        self.setItem(src_row, src_col, QtGui.QTableWidgetItem(dest_value))
        #src_value = item_src.text()
        #item_src.setText(item_dest.text())
        #item_dest.setText(item_src.text())

class Login(QtGui.QDialog):
     def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setWindowTitle('Google Play Music Login')
        self.resize(500, 60)
        self.textName = QtGui.QLineEdit(self)
        self.textPass = QtGui.QLineEdit(self)
        self.textPass.setEchoMode(QLineEdit.Password)
        self.buttonLogin = QtGui.QPushButton('Login', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.textName)
        layout.addWidget(self.textPass)
        layout.addWidget(self.buttonLogin)
     def closeEvent(self, evnt):
          super(Login, self).closeEvent(evnt)
          sys.exit()
     def handleLogin(self):
        if self.textName.text() != '' and self.textPass.text() != '':
            self.accept()

        else:
            QtGui.QMessageBox.warning(
                self, 'Error', 'Please enter the username and password')

     def getCreds(self):
          return [self.textName.text(), self.textPass.text()]

class GMusicUtility(QtGui.QWidget):
     mc = None # Mobileclient interface

     mm = None # Musicmanager interface

     dropBoxClient = None # Dropbox interface

     # playlist header used on all exports
     csvHeader = "Track ID,Track Name,Album,Artist,Track Number,Year,Album Artist,Disc Number,Genre,Date Added\n"

     # HTML header used on all exports
     HTMLHeader = None

     # HTML Footer used on all exports
     HTMLFooter = "</TABLE>\n</BODY>\n</HEAD>\n</HTML>"

     playlists = None

     library = None

	 # App Version - Used to check for updates
     version = "3.3"

     # Export As ComboBox
     libraryExportFormatComboBox = None

     # Export As label
     playlistExportFormatLabel = None

     # Export As Option Menu
     playlistExportFormatComboBox = None

     # Library Task label
     libraryTaskLabel = None

     # Library tasks ComboBox
     libraryTaskComboBox = None

     # Playlist label - needs to be dynamically show and hidden as needed
     playlistLabel = None

     # Playlist ComboBox - needs to be dynamically show and hidden as needed
     playlistComboBox = None

     # 2nd playlist used when comparing 2 playlists
     
     # Playlist label - needs to be dynamically show and hidden as needed
     playlistLabel2 = None

     # Playlist ComboBox - needs to be dynamically show and hidden as needed
     playlistComboBox2 = None
     
     # Playlist Task ComboBox
     playlistTaskComboBox = None

     # Rename Playlist Table
     renameTable = None

     # Rename Playlist Widget
     renameWidget = None

	# Recently Added Widget
     recentlyAddedWidget = None

     recentlyAddedLabel = None

     recentlyAddedDateEdit = None

     table_view = None

     recentlyAddedLayout = None

     recentlyAddedYear = 0

     recentlyAddedMonth = 0

     recentlyAddedDay = 0

     newSongs=None;
     
     # Window width & height
     width = 850
     height = 150

     # Coordinates for the controls for each column (X coordinate)
     columnXCoordinates = [15, 275, 530]

     # Coordinates for the controls for each row (Y coordinate)
     rowYCoordinates = [20, 40, 80, 100]

     validFormats = ["CSV", "HTML"]

     def __init__(self, username, password):
          super(GMusicUtility, self).__init__()

          # If the user wants to see the command line usage, call commandLineUsage() and exit without authenticating
          if len(sys.argv) > 1 and (sys.argv[1] == "/help" or sys.argv[1] == "/?"):
               self.commandLineUsage()
               sys.exit()

		# Before logging in, check my site to see if  there is an update for this script
          http = urllib3.PoolManager()

          # Wrap the request to get the latest version from my server with try because if mt site is down or not accessible, this will raise a MaxRetryError
          try:
               with http.request('GET', 'http://www.hovav.org/GMusicUtility/latestversion.txt', preload_content=False) as resp:
                    # Try to convert the value returned from the server to float. If the server returned a proper
                    # response, this will succeed or throw an error if the server returned an error page
                    try:
                         if float(resp.data) > float(self.version):
                              # When no command line arguments were provided, prompt the user to download update. Otherwise when using command line only print out message to console
                              if len(sys.argv) <= 1:
                                   result = self.messageBox_YesNo("Google Play Music Utility Updater", "There is an updated version of this script available. Would you like to download it now ?")

                                   if result == "YES":
                                        webbrowser.open('http://apps.hovav.org/google-play-music-utility/')
                              else:
                                   print "There is an updated version of this script available. Please visit http://apps.hovav.org/google-play-music-utility/ to download an updated version"
                    except:
                         pass

               # Release the http connection
               resp.release_conn()
          except:
               pass

          self.mc = Mobileclient()

          # We have to use the Musicmanager interface to download music
          self.mm = Musicmanager()

          # Supress insecure warnings
          logging.captureWarnings(True)

          if self.mc.login(username, password, "") == False:
               # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
               if len(sys.argv) == 1:
                    self.messageBox("Google Play Music Utility", "Unable to log into your Google account. Please check your login credentials")
                    sys.exit()
               else:
                    print "Unable to log into your Google account. Please check your login credentials"
                    sys.exit()

          if tableForegroundColor is None or tableBackgroundColor is None:
               # Default
               self.HTMLHeader = "<HTML>\n<HEAD>\n<STYLE>\ntable td {\nborder: 0.5px solid black;\nborder-collapse: collapse;\ncellpadding: 0px;\nbackground-color:#FFFFFF;\ncolor:black;\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1 cellspacing=0>\n<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD><TD>Date Added</TD></TR>\n"
          elif tableForegroundColor is not None and tableBackgroundColor is not None:
               # Validate the provided foreground and background colors.

               _rgbstring = re.compile(r'#[a-fA-F0-9]{6}$')

               # Validate that tableForegroundColor is a valid hex number
               if bool(_rgbstring.match(tableForegroundColor)) == False:
                    self.messageBox("Recently Added", "tableForegroundColor is not a valid hex number. Please use only 0-9 and A-F with a leading #")
                    sys.exit()

               # Validate that tableBackgroundColor is a valid hex number
               if bool(_rgbstring.match(tableBackgroundColor)) == False:
                    self.messageBox("Recently Added", "tableBackgroundColor is not a valid hex number. Please use only 0-9 and A-F with a leading #")
                    sys.exit()

               self.HTMLHeader = "<HTML>\n<HEAD>\n<STYLE>\ntable td {\n     border-style: solid;\n    border-width: 0px;\n    border-color:red;\n    background-color:" + str(tableBackgroundColor) + ";\n    color:" + str(tableBackgroundColor) + ";\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1>\n<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD><TD>Date Added</TD></TR>\n"
          # parse command line arguments before loading any data from the web.
          self.parseCommandLineArguments()

          self.buildMainWindow()

     # Build the main screen
     def buildMainWindow(self):
          self.resize(self.width, self.height)
          self.setWindowTitle('Google Play Music Utility ' + self.version + " Written by Segi Hovav")

          leftPadding = 45

          ### Column 1 ###

          # Playlist Task Options Label
          self.playlistTaskLabel = QtGui.QLabel(self)
          self.playlistTaskLabel.setText("Playlist Options")
          self.playlistTaskLabel.move(self.columnXCoordinates[0], self.rowYCoordinates[0])

          # Playlist Task ComboBox
          self.playlistTaskComboBox = QtGui.QComboBox(self)
          self.playlistTaskComboBox.addItem(None)
          self.playlistTaskComboBox.addItem("Create a playlist from CSV")
          self.playlistTaskComboBox.addItem("Delete a playlist")
          self.playlistTaskComboBox.addItem("Download all songs in a playlist")
          self.playlistTaskComboBox.addItem("Duplicate a playlist")
          self.playlistTaskComboBox.addItem("Export a playlist")
          self.playlistTaskComboBox.addItem("Export all playlists")
          self.playlistTaskComboBox.addItem("Find duplicates tracks in playlists")
          self.playlistTaskComboBox.addItem("Rename a playlist")
          # self.playlistTaskComboBox.addItem("Reorder a playlist")

          self.playlistTaskComboBox.move(self.columnXCoordinates[0], self.rowYCoordinates[1])
          self.playlistTaskComboBox.activated[str].connect(self.playlistTaskComboBoxChange)

          # Library Task Label
          self.libraryTaskLabel = QtGui.QLabel(self)
          self.libraryTaskLabel.setText("Library Options")
          self.libraryTaskLabel.move(self.columnXCoordinates[0], self.rowYCoordinates[2])

          # Library Task ComboBox
          self.libraryTaskComboBox = QtGui.QComboBox(self)
          self.libraryTaskComboBox.addItem(None)
          self.libraryTaskComboBox.addItem("Export your entire library")
          self.libraryTaskComboBox.addItem("View recently added files")
          self.libraryTaskComboBox.activated[str].connect(self.libraryTaskComboBoxChange)
          self.libraryTaskComboBox.move(self.columnXCoordinates[0], self.rowYCoordinates[3])

          ### Column 2 ###

          # Playlist Label
          self.playlistLabel = QtGui.QLabel(self)
          self.playlistLabel.setText("Playlist")
          self.playlistLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[0])
          self.playlistLabel.hide()

          # Playlist ComboBox
          self.playlistComboBox = QtGui.QComboBox(self)
          self.playlistComboBox.setObjectName("playlistComboBox") # Set the playlist combobox name so we can use it for validation when comparing 2 playlists
          self.playlistComboBox.move(self.columnXCoordinates[2]+(leftPadding), self.rowYCoordinates[0])
          self.playlistComboBox.activated[str].connect(self.playlistComboBoxChange)

          # Library Export Format Label
          self.libraryExportFormatLabel = QtGui.QLabel(self)
          self.libraryExportFormatLabel.setText("Export as")

          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.libraryExportFormatLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[2])
          self.libraryExportFormatLabel.hide()

          # Library Export Format ComboBox
          self.libraryExportFormatComboBox = QtGui.QComboBox(self)
          self.libraryExportFormatComboBox.addItem(None)
          self.libraryExportFormatComboBox.addItem("CSV")
          self.libraryExportFormatComboBox.addItem("HTML")
          self.libraryExportFormatComboBox.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[3])
          self.libraryExportFormatComboBox.activated[str].connect(self.libraryExportFormatComboBoxChange)
          self.libraryExportFormatComboBox.hide()

          # Recently Added Label
          self.recentlyAddedLabel = QtGui.QLabel(self)
          self.recentlyAddedLabel.setText("Added since")

          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.recentlyAddedLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[2])
          self.recentlyAddedLabel.hide()

          # Recently Added ComboBox
          self.recentlyAddedDateEdit = QtGui.QDateEdit(self)
          self.recentlyAddedDateEdit.setCalendarPopup(True)
          self.recentlyAddedDateEdit.setDisplayFormat('MM/dd/yyyy')
          self.recentlyAddedDateEdit.setFixedWidth(130)

          # Set the default date to current date-30 days
          d = date.today() - timedelta(days=30)
          self.recentlyAddedDateEdit.setDate(d)

          # This must be called for the event handler to work
          self.recentlyAddedDateEdit.calendarWidget().installEventFilter(self)

          # Bind the event when the date changes
          self.recentlyAddedDateEdit.connect(self.recentlyAddedDateEdit.calendarWidget(), QtCore.SIGNAL('selectionChanged()'), self.recentlyAddedDateEditChange)

          # Event when the user types in the QDateEdit control. Keyboard presses are ignore because events are triggered as soon as the control changes
          self.recentlyAddedDateEdit.connect(self.recentlyAddedDateEdit, QtCore.SIGNAL('keyPressEvent()'), self.recentlyAddedDateEditKeypress)

          # Move the date dropdown to the same location as self.libraryExportFormatComboBox
          self.recentlyAddedDateEdit.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[3])

          # Hide it initially
          self.recentlyAddedDateEdit.hide()

          self.playlistComboBox.hide()
          self.playlistComboBox.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[1])
          self.playlistComboBox.activated[str].connect(self.playlistComboBoxChange)

          ### Column 3 ###

          # Export Format Label
          self.playlistExportFormatLabel = QtGui.QLabel(self)
          self.playlistExportFormatLabel.setText("Export as")

          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatLabel.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[0])
          self.playlistExportFormatLabel.hide()

          # Export Format ComboBox
          self.playlistExportFormatComboBox = QtGui.QComboBox(self)
          self.playlistExportFormatComboBox.addItem(None)
          self.playlistExportFormatComboBox.addItem("CSV")
          self.playlistExportFormatComboBox.addItem("HTML")
          self.playlistExportFormatComboBox.hide()

          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatComboBox.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[1])
          self.playlistExportFormatComboBox.activated[str].connect(self.playlistExportFormatComboBoxChange)
          
          # Playlist Label for 2nd playlist
          self.playlistLabel2 = QtGui.QLabel(self)
          self.playlistLabel2.setText("2nd Playlist")
          self.playlistLabel2.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[0])
          self.playlistLabel2.hide()

          # Playlist ComboBox for 2nd playlist
          self.playlistComboBox2 = QtGui.QComboBox(self)
          self.playlistComboBox2.setObjectName("playlistComboBox2") # Set the playlist combobox name so we can use it for validation when comparing 2 playlists
          self.playlistComboBox2.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[1])
          self.playlistComboBox2.activated[str].connect(self.playlistComboBoxChange)
          self.playlistComboBox2.hide()
          
          # Load all playlists into the playlist ComboBox. I do this here because both playlists have to be initialized first
          self.loadPlaylists()

          self.show()

     # Create the rename a playlist window
     def buildRecentlyAddedWindow(self, asOf=None, fileName=None, exportFormat=None, saveToDropbox=False):
          # Date to find songs that have been added since 30 days ago
          #asofDate=date.today() - timedelta(days=30)

          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               if asOf is None:
                    self.messageBox("Recently Added", "Invalid exportFormat type " + exportFormat)
               else:
                    print "Recently Added: Invalid exportFormat type " + exportFormat
               return

          # Build date object based on function parameter asOf if given, otherwise use the value in DateTimeEdit control
          if asOf is None:
               asofDate = datetime.date(self.recentlyAddedYear, self.recentlyAddedMonth, self.recentlyAddedDay)
          else:
               asofDate = datetime.date(asOf.year, asOf.month, asOf.day)

          self.newSongs = []

          # Convert date from seconds to Microseconds (Milliseconds*1000)
          asofDateMS = time.mktime(asofDate.timetuple()) * 1000000

          asofDateMS = int(asofDateMS)

		# Add all songs with creationTimestamp > asofDate to an array
          for currNewSong in self.library:
               if long(self.library[currNewSong][9]) > asofDateMS:
                    # if we are exporting to CSV, get all available columns from self.library
                    if fileName is not None:
                         self.newSongs.append([self.library[currNewSong][0], self.library[currNewSong][1], self.library[currNewSong][2], self.library[currNewSong][3], self.library[currNewSong][4], self.library[currNewSong][5], self.library[currNewSong][6], self.library[currNewSong][7], self.library[currNewSong][8]])
                    else:
                         # Otherwise, only add Artist,Album,Track,Track Number and Date Added
                         self.newSongs.append([self.library[currNewSong][3], self.library[currNewSong][2], self.library[currNewSong][1], self.library[currNewSong][4],str(datetime.datetime.fromtimestamp(float(int(self.library[currNewSong][9])/1000000)))])

          # When we are saving to Dropbox from the command line, create a default file name since one won't be provided
          if fileName is None:
                    fileName = "RecentlyAdded as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower()

          # Sort by Artist (Index 1)
          self.newSongs = sorted(self.newSongs, key=lambda newsong: newsong[0], reverse=True)

          if len(self.newSongs) == 0:
               # If asOf is None, this function was not called from the command line
               if asOf is None:
                    self.messageBox("Recently Added", "There were no songs added since the specified date")
               else:
                    print "There were no songs added since the specified date"
               return

          # When command line arguments were provided use them here
          if asOf is not None:
               recentlyAddedFile = open(fileName, "w")
            
               csvHeader = "Track ID,Track Name,Album,Artist,Track Number,Year,Album Artist,Disc Number,Genre,Date Added\n"
               HTMLHeader = self.HTMLHeader = "<HTML>\n<HEAD>\n<STYLE>\ntable td {\nborder: 0.5px solid black;\nborder-collapse: collapse;\ncellpadding: 0px;\nbackground-color:#FFFFFF;\ncolor:black;\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1 cellspacing=0>\n<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD><TD>Date Added</TD></TR>\n"
               
               # CSV Header
               if exportFormat == "CSV":
                    recentlyAddedFile.write(csvHeader)
               elif exportFormat == "HTML":
                    recentlyAddedFile.write(HTMLHeader)

               for currNewSong in self.newSongs:
                    currTrack = self.library[currNewSong[0]]

                    if exportFormat == "CSV":
                         recentlyAddedFile.write('"' + currTrack[0].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[1].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[2].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[3].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write(str(currTrack[4]) + ',')
                         recentlyAddedFile.write(str(currTrack[5]) + ',')
                         recentlyAddedFile.write('"' + currTrack[6].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write(str(currTrack[7]) + ',')
                         recentlyAddedFile.write('"' + currTrack[8].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + str(datetime.datetime.fromtimestamp(float(int(currTrack[9])/1000000))) + '"\n')
                    elif exportFormat == "HTML":
                         # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                         if currTrack[0] == "": currTrack[0] = "&nbsp;"
                         if currTrack[1] == "": currTrack[1] = "&nbsp;"
                         if currTrack[2] == "": currTrack[2] = "&nbsp;"
                         if currTrack[3] == "": currTrack[3] = "&nbsp;"
                         if currTrack[4] == "": currTrack[4] = "&nbsp;"
                         if currTrack[5] == "": currTrack[5] = "&nbsp;"
                         if currTrack[6] == "": currTrack[6] = "&nbsp;"
                         if currTrack[7] == "": currTrack[7] = "&nbsp;"
                         if currTrack[8] == "": currTrack[8] = "&nbsp;"
                         if currTrack[9] == "": currTrack[9] = "&nbsp;"

                         recentlyAddedFile.write("<TR>")
                         recentlyAddedFile.write("<TD>" + currTrack[0].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[1].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[2].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[3].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + str(currTrack[4]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + str(currTrack[5]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[6].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")

                         recentlyAddedFile.write("<TD>" + str(currTrack[7]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[8].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + str(datetime.datetime.fromtimestamp(float(int(currTrack[9])/1000000))) + "</TD>")
                         recentlyAddedFile.write("</TR>\n")

               if exportFormat == "HTML":
                    recentlyAddedFile.write(self.HTMLFooter)

               recentlyAddedFile.close()

               if fileName is not None:
                    if saveToDropbox == True:
                         # Log into Dropbox using OAuth so we can read and write to it
                         if self.performDropboxOAuth() == False:
                              return

                         # Write the file to Dropbox
                         with open(fileName, 'rb') as output:
                              response = self.dropBoxClient.put_file(fileName, output)

                              output.close()

                              os.remove(fileName)

                    sys.exit()

          self.recentlyAddedWidget = QtGui.QWidget()
          self.recentlyAddedWidget.showMaximized()
          self.recentlyAddedWidget.setWindowTitle("Click on column title to sort")
          
          table_model = TableModel(self,self.newSongs, ["Artist", "Album", "Track", "Track Number","Date Added"])

          self.table_view = TableView()
          self.table_view.setModel(table_model)
          
          self.table_view.resizeColumnsToContents()

          # set font
          font = QFont("Courier New", 14)

          self.table_view.setFont(font)

          # set column width to fit contents (set font first!)
          self.table_view.resizeColumnsToContents()

          # enable sorting
          self.table_view.setSortingEnabled(True)

          '''
          self.table_view.setDragEnabled(True)
          self.table_view.setAcceptDrops(True)
          self.table_view.setDragDropOverwriteMode(True)
          self.table_view.setDragDropMode(QAbstractItemView.InternalMove)
          self.table_view.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
          self.table_view.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
          '''

          self.recentlyAddedLayout = QVBoxLayout(self.recentlyAddedWidget)
          
          self.buttonExportRecentlyAdded = QtGui.QPushButton('Export Results')
          self.buttonExportRecentlyAdded.clicked.connect(self.exportRecentlyAdded)
          self.recentlyAddedLayout.addWidget(self.buttonExportRecentlyAdded)
          
          self.recentlyAddedLayout.addWidget(self.table_view)
          self.recentlyAddedWidget.setLayout(self.recentlyAddedLayout)

          if self.recentlyAddedYear == 0:
               self.recentlyAddedWidget.show()

     # Command line parameters
     def commandLineUsage(self):
          print
          print "Google Play Music Utility command line arguments:"
          print
          print "Help: /help=command line usage"
          print
          print "Current export formats can be either CSV or HTML"
          print
          print "Create playlist from CSV: " + sys.argv[0] + " /createplaylist playlistname filename.csv\nEx: " + sys.argv[0] + " /createplaylist Rock Rock.csv"
          print
          print "Delete a playlist (Careful. There's no confirmation with the command line. The playlist gets deleted immediately):" + sys.argv[0] + " /deleteplaylist playlistname\nEx: " + sys.argv[0] + " /deleteplaylist Rock"
          print
          print "Download all songs in a playlist (Locally): " + sys.argv[0] + " /downloadplaylist playlistname path\nEx: " + sys.argv[0] + " /downloadplaylist Rock c:\playlists"
          print
          print "Download all songs in a playlist (Dropbox): " + sys.argv[0] + " /downloadplaylist playlistname Dropbox\nEx: " + sys.argv[0] + " /downloadplaylist Rock Dropbox"
          print
          print "Duplicate a playlist: " + sys.argv[0] + " /duplicateplaylist playlistname newplaylistname\nEx: " + sys.argv[0] + " /duplicateplaylist Rock Rock2"
          print
          print "Export a playlist (Locally): " + sys.argv[0] + " /exportplaylist playlistname path format\nEx: " + sys.argv[0] + " /exportplaylist Rock c:\RockPlaylist.csv CSV"
          print
          print "Export a playlist (Dropbox): " + sys.argv[0] + " /exportplaylist playlistname Dropbox format\nEx: " + sys.argv[0] + " /exportplaylist Rock Dropbox CSV"
          print
          print "Export all playlists (Locally): " + sys.argv[0] + " /exportallplaylists path format\nEx: " + sys.argv[0] + " /exportallplaylists c:\playlists HTML"
          print
          print "Export all playlists (Dropbox): " + sys.argv[0] + " /exportallplaylists Dropbox format\nEx: " + sys.argv[0] + " /exportallplaylists Dropbox HTML"
          print
          print "Export library (Locally): " + sys.argv[0] + " /exportlibrary path format\nEx: " + sys.argv[0] + " /exportlibrary c:\MyLibrary CSV"
          print
          print "Export library (Dropbox): " + sys.argv[0] + " /exportlibrary Dropbox format\nEx: " + sys.argv[0] + " /exportlibrary Dropbox CSV"
          print
          print "Find Duplicate Tracks In Playlist (Locally): " + sys.argv[0] + " /findduplicates 1stplaylist 2ndplaylist filename.csv\nEx: " + sys.argv[0] + " /findduplicates Rock Misc c:\MyLibrary CSV"
          print
          print "Find Duplicate Tracks In Playlist (Dropbox): " + sys.argv[0] + " /findduplicates 1stplaylist 2ndplaylist Dropbox\nEx: " + sys.argv[0] + " /exportlibrary Rock Misc Dropbox"
          print
          print "Recently added since (Locally): " + sys.argv[0] + " /recentlyadded addedsincedate filename format\nEx: " + sys.argv[0] + " /recentlyadded 02/28/2015 recentlyadded.csv CSV"
          print
          print "Recently added since (Dropbox): " + sys.argv[0] + " /recentlyadded addedsincedate Dropbox format\nEx: " + sys.argv[0] + " /recentlyadded 02/28/2015 Dropbox CSV"
          print
          print "Rename a playlist: " + sys.argv[0] + " /renameplaylist playlistname newplaylistname\nEx: " + sys.argv[0] + " /renameplaylist Rock Rock2"
          print

          sys.exit()
      
     # Create a playlist from an exported CSV file
     def createPlaylistFromCSV(self, newPlaylistName=None, fileName=None):
          importFile = None

          # If no command line parameters were given
          if newPlaylistName is None:
               # Display the prompt modally
               newPlaylistName = self.showDialog("Create playlist from CSV", "Please enter the name of the playlist that you want to create")

               # When the dialog result is None, the user cancelled the dialog or clicked on OK without entering a playlist name
               if newPlaylistName == None or newPlaylistName == "":
                    return

               # Check to see if there is already a playlist with the same name as the one that will be created
               # If there is one, confirm with the user that they want to create a duplicate playlist
               playlistNames = []

               # Add all playlist names to an array
               for playlist in self.playlists:
                    playlistNames.append(playlist["name"])

               # Sort the array
               playlistNames.sort()

               # Loop through all playlists. If the new playlist name chosen is in use, confirm with the user before creating a new playlist with the same name as another existing playlist
               for playlist in playlistNames:
                    if playlist == newPlaylistName and AllowDuplicatePlaylistNames == False:
                         result = self.messageBox_YesNo("Playlist name exists already", "The new playlist name that you entered exists already. Are you sure that you want to use this playlist name anyways ?")

                         if result == "NO":
                              return

          # if fileName wasn't provided from the command line arguments, prompt for it

          if fileName is None:
               # Prompt for the CSV to open. This will open the file for reading
               fileName, filter = QtGui.QFileDialog.getOpenFileName(self, 'Choose the CSV to create the playlist from', selectedFilter='*.csv')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False

               if fileName[-4:].upper() != ".CSV":
                    self.messageBox("Create Playlist From Export", "The file to create the playlist from must be a CSV file")
                    return

          try:
               # open the file for reading
               importFile = open(fileName, "r")
          except:
               print "An error occurred opening " + str(fileName)
               sys.exit()
          # read all lines from the file
          lines = importFile.readlines()

          # Verify the file selected by making sure that the first line of the CSV matches the playlist CSV header
          if lines[0] != self.csvHeader:
               # When no command line arguments were provided, use MessageBox. Otherwise print the error message to the console
               if fileName is None:
                    self.messageBox("Create Playlist From Export", "An error occurred reading the CSV that you selected. The header does not match")
                    return
               else:
                    sys.exit()

          # Create the new playlist and store the new playlist id
          newPlaylistId = self.mc.create_playlist(newPlaylistName)

          # loop though all rows
          for num in range(1, len(lines)):
               # Strip the trailing newline from the current line
               currLine = lines[num].rstrip()

               # get everything up the first comma which is the track id
               firstDelim = currLine.find(chr(34) + ",")

               # add it to the new playlist
               self.mc.add_songs_to_playlist(newPlaylistId, currLine[1:firstDelim])

          # close the file
          importFile.close()

          if len(sys.argv) > 1:
               sys.exit()
          else:
               self.messageBox("Create Playlist from CSV", "The playlist " + newPlaylistName + " has been created")

               # Reload the playlists from the server
               self.loadPlaylists()

     # Event when the user clicks on a playlist that will be deleted
     def deletePlaylist(self, playlistName, forceConfirmation=None):
          # If no playlist name was provided at the command line, display confirmation twice before deleting the playlist
          if playlistName is None or forceConfirmation == True:
               # Confirm before deleting a playlist
               result = self.messageBox_YesNo("Delete Playlist", "Are you sure that you want to delete the playlist " + playlistName + " ?")

               if result != 'YES':
                    return

               # Confirm a 2nd time
               result = self.messageBox_YesNo("Delete Playlist", "Are you 100% sure that you want to delete the playlist " + playlistName + " ?")

               if result != 'YES':
                    return

          # Get the playlist id for the specified playlist name
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    deletePlaylistID = playlist["id"]

          # API call to delete the playlist
          self.mc.delete_playlist(deletePlaylistID)

          # Reload the playlists from the server since we just deleted a playlist in case the user wants to delete another playlist
          if len(sys.argv) == 1:
               self.messageBox("Delete a Playlist", "The playlist " + playlistName + " has been deleted")

               self.loadPlaylists()
          else:
               sys.exit()

     # Event when the user clicks on Download all songs in a playlist
     def downloadPlaylistToDirectory(self, playlistName, downloadPath=None, saveToDropbox=False):
          # Log into Google using OAuth so we can use the Musicmanager interface
          if self.performGoogleOAuth() == False:
               print "returning after self.performGoogleOAuth()"
               return

          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if downloadPath is None and saveToDropbox == True:
               saveLocation = "Dropbox"
          elif downloadPath is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

          if saveLocation == "Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

               # Create a folder in Dropbox based on the playlist name chosen. If the folder exists already, we renamed the older folder to playlistName-old. If playlistName-old folder exists already, it is deleted first
               try:
                    folder_metadata = self.dropBoxClient.metadata("/" + playlistName, include_deleted=False)

                    if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                         # If the folder named playlistName already existed in the past but was deleted
                         if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                              # self.messageBox("The folder /" + playlistName + " exists already and will be renamed to /" + playlistName + "-old. If the folder /" + playlistName + "-old exists already, it will be deleted")

                              # Check to see whether the folder playlistName-old exists. If it does, delete it
                              try:
                                   folder_metadata = self.dropBoxClient.metadata("/" + playlistName + "-old", include_deleted=False)

                                   # If the folder named playlistName-old already existed in the past but was deleted
                                   if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                                        # Delete the playlistName-old folder
                                        try:
                                             self.dropBoxClient.file_delete("/" + playlistName + "-old")
                                        except dbrest.ErrorResponse, e:
                                             print "An error occurred deleting the folder /" + playlistName + "-old with the error %s" % (e,)
                                             sys.exit()
                              except dbrest.ErrorResponse, e:
                                   pass  # We need to catch this Exception when the folder playlistName-old doesn't exist which may be OK (it doesn't have to exist already)

                              # Rename the folder playlistName to playlistName-old
                              try:
                                   self.dropBoxClient.file_move("/" + playlistName, "/" + playlistName + "-old")
                              except dbrest.ErrorResponse, e:
                                   print "An error occurred renaming the folder /" + playlistName + " to /" + playlistName + "-old with the error %s" % (e,)
                                   sys.exit()
               except dbrest.ErrorResponse, e:
                    # pass # We need to catch this Exception when the folder playlistName doesn't exist which may be OK (it doesn't have to exist already)

                    # Create the playlist folder
                    try:
                         print "Creating the folder /" + playlistName
                         self.dropBoxClient.file_create_folder("/" + playlistName)
                    except dbrest.ErrorResponse, e:
                         print "An error occurred creating the folder /" + playlistName + " with the error %s" % (e,)
          elif saveLocation == "Cancel":
               return

          # Look for the specified playlist
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         # Make API call to get the suggested file and audio byte string
                         filename, audio = self.mm.download_song(self.library[track['trackId']][0])

                         if saveLocation == "Locally":
                              # If path wasn't given at the command line prompt for it
                              if downloadPath is None:
                                   downloadPath = QtGui.QFileDialog.getExistingDirectory(parent=self, dir="/", caption='Please select a directory')

                                   if downloadPath == "" or downloadPath is None:
                                       return

                              # Determine the delimiter based on the O.S.
                              if sys.platform == "win32":
                                   downloadPath = downloadPath.replace("/", "\\")
                                   delimiter = "\\"
                              else:
                                   delimiter = "/"

                              with open(downloadPath + delimiter + filename, 'wb') as f:
                                   # Write the audio buffer
                                   print "Downloading " + downloadPath + delimiter + filename
                                   f.write(audio)
                                   f.close()

                                   # Make the Artist folder if it doesn't exist
                                   if os.path.isdir(downloadPath + delimiter + self.library[track['trackId']][3]) == False:
                                        os.mkdir(downloadPath + delimiter + self.library[track['trackId']][3])

                                   # Make the Album folder if it doesn't exist
                                   if os.path.isdir(downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2]) == False:
                                        os.mkdir(downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2])

                                   # Move the song to the appropriate subdirectory
                                   print "Moving the file " + downloadPath + delimiter + filename + " to " + downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2] + delimiter

                                   # os.rename will fail if the file exists already so verify if the file exists and delete it if it does
                                   if os.path.isfile(downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2] + delimiter + filename) == True:
                                        os.remove(downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2] + delimiter + filename)

                                   os.rename(downloadPath + delimiter + filename, downloadPath + delimiter + self.library[track['trackId']][3] + delimiter + self.library[track['trackId']][2] + delimiter + filename)
                         elif saveLocation == "Dropbox":
                              # Create the folder named after the artist if it doesn't exist already
                              try:
                                   folder_metadata = self.dropBoxClient.metadata("/" + playlistName + "/" + self.library[track['trackId']][3], include_deleted=False)

                                   if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                                        try:
                                             self.dropBoxClient.file_create_folder("/" + playlistName + "/" + self.library[track['trackId']][3])
                                        except dbrest.ErrorResponse, e:
                                             pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already
                                             #print("An error occurred creating the folder /" + playlistName + "/" + self.library[track['trackId']][3] + " with the error %s" % (e,))
                              except dbrest.ErrorResponse, e:
                                   try:
                                        self.dropBoxClient.file_create_folder("/" + playlistName + "/" + self.library[track['trackId']][3])
                                   except dbrest.ErrorResponse, e:
                                        pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already
                                        #print("An error occurred creating the folder /" + playlistName + "/" + self.library[track['trackId']][3] + " with the error %s" % (e,))

                              # Create the folder named after the album if it doesn't exist already
                              try:
                                   folder_metadata = self.dropBoxClient.metadata("/" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2], include_deleted=False)

                                   if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                                        try:
                                             self.dropBoxClient.file_create_folder("/" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2])
                                        except dbrest.ErrorResponse, e:
                                             pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already
                                             #print("An error occurred creating the folder /" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2] + " with the error %s" % (e,))
                              except dbrest.ErrorResponse, e:
                                   try:
                                        self.dropBoxClient.file_create_folder("/" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2])
                                   except dbrest.ErrorResponse, e:
                                        pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already
                                        #print("An error occurred creating the folder /" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2] + " with the error %s" % (e,))

                              # We have to write the file locally first before we can upload it to Dropbox
                              with open(filename, 'wb') as input:
                                   input.write(audio)
                                   input.close()

                              # Write the file to Dropbox
                              with open(filename, 'rb') as output:
                                   response = self.dropBoxClient.put_file(filename, output)

                                   # Move the file to Artist/Album folder
                                   response = self.dropBoxClient.file_move("/" + filename, "/" + playlistName + "/" + self.library[track['trackId']][3] + "/" + self.library[track['trackId']][2] + "/" + filename)

                                   output.close()

                                   os.remove(filename)

          # When the user is not using command line arguments display message indicating that the download has finished using MessageBox. Otherwise print to console
          if len(sys.argv) <= 1:
               self.messageBox("Download a playlist", "The download of the playlist " + playlistName + " has finished")
          else:
               print "The download of the playlist " + playlistName + " has finished"
          return

     # Event when the user clicks on a playlist to be duplicated
     def duplicatePlaylist(self, playlistName, newPlaylistName=None, isRenaming=False):
          # If no command line arguments were given, prompt for the name of the playlist to create
          if newPlaylistName is None:
               # Display the prompt modally
               newPlaylistName = self.showDialog("Duplicate a playlist", "Please enter the name of the playlist that you want to create")

               # When the dialog result is None, the user cancelled the dialog or clicked on OK without entering a playlist name
               if newPlaylistName == None or newPlaylistName == "":
                    self.playlistExportFormatComboBox.hide()
                    self.playlistExportFormatLabel.hide()

                    return

          # If AllowDuplicatePlaylistNames is False, check to see if there is already a playlist with the same name as the one that will be created. If there is one, confirm with the user that they want to create a duplicate playlist
          if AllowDuplicatePlaylistNames == False:
               playlistNames = []

               # Add all playlist names to an array
               for playlist in self.playlists:
                    playlistNames.append(playlist["name"])

               # Sort the array
               allPlaylistNames = sorted(playlistNames)

               # Loop through all playlists. If the new playlist name chosen is in use, confirm with the user before creating a new playlist with the same name as another existing playlist
               for playlist in allPlaylistNames:
                    # Only display this message when we are not working from the command line. parseCommandLineArguments() will verify that the playlist doesn't exist already when using command line arguments
                    if playlist == newPlaylistName and newPlaylistName is None:
                         result = self.messageBox_YesNo("Playlist name exists already", "The new playlist name that you entered exists already. Are you sure that you want to use this playlist name anyways ?")

                         if result != 'YES':
                              return

          # Create the new playlist and store the new playlist id
          newPlaylistId = self.mc.create_playlist(newPlaylistName)

          # Loop through all tracks in the playlist and add each one to the new playlist
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         self.mc.add_songs_to_playlist(newPlaylistId, track['trackId'])

          # When isRenaming is True, delete the playlist after it has been duplicated
          if isRenaming == True:
               # Get the playlist id for the specified playlist name
               for playlist in self.playlists:
                    # Delete the original playlist
                    if playlist["name"] == playlistName:
                         # API call to delete the playlist
                         self.mc.delete_playlist(playlist["id"])

          # When a command line argument was passed terminate the application
          if len(sys.argv) > 1:
               sys.exit()
          else:
               if isRenaming == True:
                    self.messageBox("Rename a playlist", "The playlist " + playlistName + " has been renamed to " + newPlaylistName)
               else:
                    self.messageBox("Duplicate a playlist", "The playlist " + playlistName + " has duplicated as " + newPlaylistName)

               # Reload the playlists from the server since we just deleted a playlist in case the user wants to delete another playlist
               self.loadPlaylists()

     # Event when the user clicks on Export All Playlists
     def exportAllPlaylists(self, exportPath=None, exportFormat=None, saveToDropbox=False):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return

          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if exportPath is None and saveToDropbox == True:
               saveLocation = "Dropbox"
          elif exportPath is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

          if saveToDropbox == True or saveLocation == "Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

          if saveLocation == "Cancel":
               return

          # If path wasn't given at the command line prompt for it
          if exportPath is None and saveToDropbox == False and saveLocation == "Locally":
               exportPath = None

               exportPath = QtGui.QFileDialog.getExistingDirectory(parent=self, dir="/", caption='Please select a directory')

               if exportPath == "" or exportPath is None:
                    return
          elif exportPath is None and (saveToDropbox == True or saveLocation == "Dropbox"):
               # When we are saving to Dropbox, create a temporary directory locally to save the playlists to before uploading them to Dropbox
               exportPath = tempfile.mkdtemp()

          if sys.platform == "win32":
               exportPath = exportPath.replace("/", "\\")
               delimiter = "\\"
          else:
               delimiter = "/"

          # playlisttracks = []

          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               # Replace any characters that are not allowed in Windows filenames with _.
               playlistname = playlist["name"].replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace(":", "_").replace(chr(34), "_").replace("<", "_").replace(">", "_").replace("|", "_")

               fileName = exportPath + delimiter + playlistname + "." + exportFormat.lower()

               currFile = open(fileName, "w")

               if exportFormat == "CSV":
                    currFile.write(self.csvHeader)
               elif exportFormat == "HTML":
                    currFile.write(self.HTMLHeader)

               # write out the data for each track in the playlist
               for track in sorted(playlist["tracks"]):
                    currTrack = self.library[track['trackId']]

                    if exportFormat == "CSV":
                         currFile.write('"' + currTrack[0].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[1].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[2].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[3].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
                         currFile.write(str(currTrack[4]) + ',')
                         
                         currFile.write(str(currTrack[5]) + ',')
                         currFile.write('"' + currTrack[6].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                         currFile.write(str(currTrack[7]) + ',')
                         currFile.write('"' + currTrack[8].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                         currFile.write('"' + str(datetime.datetime.fromtimestamp(float(int(currTrack[9])/1000000))) + '"\n')
                    elif exportFormat == "HTML":
                         # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                         if currTrack[0] == "": currTrack[0] = "&nbsp;"
                         if currTrack[1] == "": currTrack[1] = "&nbsp;"
                         if currTrack[2] == "": currTrack[2] = "&nbsp;"
                         if currTrack[3] == "": currTrack[3] = "&nbsp;"
                         if currTrack[4] == "": currTrack[4] = "&nbsp;"
                         if currTrack[5] == "": currTrack[5] = "&nbsp;"
                         if currTrack[6] == "": currTrack[6] = "&nbsp;"
                         if currTrack[7] == "": currTrack[7] = "&nbsp;"
                         if currTrack[8] == "": currTrack[8] = "&nbsp;"

                         currFile.write("<TR>")
                         currFile.write("<TD>" + currTrack[0].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[1].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[2].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[3].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + str(currTrack[4]) + "</TD>")
                         currFile.write("<TD>" + str(currTrack[5]) + "</TD>")
                         currFile.write("<TD>" + currTrack[6].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + "</TD>")

                         currFile.write("<TD>" + str(currTrack[7]) + "</TD>")
                         currFile.write("<TD>" + currTrack[8].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + "</TD>")
                         currFile.write("<TD>" + str(datetime.datetime.fromtimestamp(float(int(currTrack[9])/1000000))) + "</TD>")
                         currFile.write("</TR>\n")

               if exportFormat == "HTML":
                    currFile.write(self.HTMLFooter)

               currFile.close()

               if saveToDropbox == True or saveLocation == "Dropbox":
                    # Change to working dir. Upload to DB will fail if we don't do this
                    os.chdir(exportPath)

                    # Write the file to Dropbox
                    with open(playlistname + "." + exportFormat.lower(), 'rb') as output:
                         response = self.dropBoxClient.put_file(playlistname + "." + exportFormat.lower(), output)

                         output.close()

                         os.remove(playlistname + "." + exportFormat.lower())

          if len(sys.argv) > 1:
               sys.exit()
          else:
               self.messageBox("Export Library", "Export All Playlists has finished")

     # Verify that the export format is valid
     def exportFormatIsValid(self, exportFormat):
          if exportFormat == "CSV" or exportFormat == "HTML":
               return True
          else:
               return False

     # Event when the user selects the export library option
     def exportLibrary(self, fileName=None, exportFormat=None, saveToDropbox=False):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return
          
          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if fileName is None and saveToDropbox == True:
               saveLocation = "Dropbox"
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return
          elif fileName is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

               # Log into Dropbox using OAuth so we can read and write to it if the save location chosen is Dropbox
               if saveLocation == "Dropbox":
                    if self.performDropboxOAuth() == False:
                         return
                    
          if saveLocation == "Cancel":
               return

          # If no filename was provided at the command line, prompt for one
          if fileName is None and saveToDropbox == False and saveLocation == "Locally":
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if exportFormat == "CSV":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the export', "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower(), "CSV (*.csv)")
               elif exportFormat == "HTML":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the export', "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower(), 'HTML (*.html)')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False
          elif fileName is None and (saveToDropbox == True or saveLocation == "Dropbox"):
               fileName = "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower()

          exportFile = open(fileName, "w")

          # Reference to entire catalog
          library = sorted(self.mc.get_all_songs())

          # librarySize = len(library)-1

          # CSV Header
          if exportFormat == "CSV":
               exportFile.write(self.csvHeader)
          elif exportFormat == "HTML":
               exportFile.write(self.HTMLHeader)

          # Loop through all tracks
          for num in range(0, len(library)-1):
               # write CSV data
               if exportFormat == "CSV":
                    exportFile.write('"' + library[num]["id"] + '",')
                    exportFile.write('"' + library[num]["title"].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + library[num]["artist"].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + library[num]["album"].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write(str(library[num].get("year","")) + ',')
                    exportFile.write('"' + library[num]["albumArtist"].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write(str(library[num]["trackNumber"]) + ',')
                    exportFile.write(str(library[num]["discNumber"]) + ',')
                    exportFile.write('"' + library[num].get("genre", "").encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + str(datetime.datetime.fromtimestamp(float(int(library[num]["creationTimestamp"])/1000000))) + '"\n')
               elif exportFormat == "HTML":
                    # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                    if library[num]["id"] == "": library[num]["id"] = "&nbsp;"
                    if library[num]["title"] == "": library[num]["title"] = "&nbsp;"
                    if library[num]["artist"] == "": library[num]["artist"] = "&nbsp;"
                    if library[num]["album"] == "": library[num]["album"] = "&nbsp;"
                    if library[num].get("year","") == "": library[num].set("year","&nbsp;")
                    if library[num]["albumArtist"] == "": library[num]["albumArtist"] = "&nbsp;"
                    if library[num]["trackNumber"] == "": library[num]["trackNumber"] = "&nbsp;"
                    if library[num]["discNumber"] == "": library[num]["discNumber"] = "&nbsp;"
                    if library[num].get("genre", "") == "": library[num].set("genre","&nbsp;")
                    if library[num].get("creationTimestamp", "") == "": library[num].set("creationTimestamp","&nbsp;")

                    exportFile.write("<TR>")
                    exportFile.write("<TD>" + library[num]["id"] + "</TD>")
                    exportFile.write("<TD>" + library[num]["title"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + library[num]["artist"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + library[num]["album"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + str(library[num].get("year","")) + "</TD>")
                    exportFile.write("<TD>" + library[num]["albumArtist"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + str(library[num]["trackNumber"]) + "</TD>")
                    exportFile.write("<TD>" + str(library[num]["discNumber"]) + "</TD>")
                    exportFile.write("<TD>" + library[num].get("genre", "").encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + str(datetime.datetime.fromtimestamp(float(int(library[num]["creationTimestamp"])/1000000))) + "</TD>")
                    exportFile.write("</TR>\n")

     #         These 2 fields for play count and rating don't retrieve the values correctly and cause the script to crash
     #          exportFile.write(str(library[num]["playCount"]) + ',')
     #          exportFile.write('"' + library[num]["rating"].encode('utf-8').strip() + '"\n')

          if exportFormat == "HTML":
               exportFile.write(self.HTMLFooter)

          exportFile.close()

          # if this function is called from the command line, this flag will be true
          if saveToDropbox == False and saveLocation == "Locally":
               if len(sys.argv) == 1:
                    self.messageBox("Export Library", "Export complete")
               else:
                    sys.exit()
          elif saveToDropbox == True or saveLocation == "Dropbox":
               # Write the file to Dropbox
               with open(fileName, 'rb') as output:
                    response = self.dropBoxClient.put_file(fileName, output)

                    output.close()

                    os.remove(fileName)

                    if len(sys.argv) == 1:
                         self.messageBox("Export Library", "Export complete")
                    else:
                         sys.exit()

     # Event when the user clicks on a playlist to export
     def exportPlaylist(self, playlistName, fileName=None, exportFormat=None, saveToDropbox=False):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return
          
          # Used to determine if the command line argument was used to invoke this function
          # so we know whether to display a messagebox when the export completes
          if fileName is not None:
               isCommandLine=True
          else:
               isCommandLine=False
               
          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if fileName is None and saveToDropbox == True:
               saveLocation = "Dropbox"
               fileName = playlistName + "." + exportFormat.lower()
          elif fileName is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

               if saveLocation == "Dropbox":
                    fileName = playlistName + "." + exportFormat.lower()
                    saveToDropbox = True

          if saveLocation == "Cancel":
               return

          # If a command line argument wasn't given prompt for the location to save the playlist
          if fileName is None and saveToDropbox == False and saveLocation == "Locally":
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if exportFormat == "CSV":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the CSV playlist', playlistName + "." + exportFormat.lower(), 'CSV (*.csv)')
               elif exportFormat == "HTML":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the HTML playlist', playlistName + "." + exportFormat.lower(), 'HTML (*.html)')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return

          exportFile = open(fileName, "w")

          playlisttracks = []

          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         playlisttracks.append(self.library[track['trackId']])

          # Sort the playlist tracks by index 0 (The track name)
          playlisttracks = sorted(playlisttracks, key=lambda playlisttrack: playlisttrack[0])

          # Heading
          if exportFormat == "CSV":
               exportFile.write(self.csvHeader)
          elif exportFormat == "HTML":
               exportFile.write(self.HTMLHeader)

          # Playlist Data
          for playlisttrack in playlisttracks:
               if exportFormat == "CSV":
                    # All double quotation marks have to be replaced with "" to be parsed correctly as a CSV
                    exportFile.write('"' + playlisttrack[0].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[1].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[2].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[3].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write(str(playlisttrack[4]) + ',')
                    exportFile.write(str(playlisttrack[5]) + ',')
                    exportFile.write('"' + playlisttrack[6].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write(str(playlisttrack[7]) + ',')
                    exportFile.write('"' + playlisttrack[8].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + str(datetime.datetime.fromtimestamp(float(int(playlisttrack[9])/1000000))) + '"\n')
               elif exportFormat == "HTML":
                    # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                    if playlisttrack[0] == "": playlisttrack[0] = "&nbsp;"
                    if playlisttrack[1] == "": playlisttrack[1] = "&nbsp;"
                    if playlisttrack[2] == "": playlisttrack[2] = "&nbsp;"
                    if playlisttrack[3] == "": playlisttrack[3] = "&nbsp;"
                    if playlisttrack[4] == "": playlisttrack[4] = "&nbsp;"
                    if playlisttrack[5] == "": playlisttrack[5] = "&nbsp;"
                    if playlisttrack[6] == "": playlisttrack[6] = "&nbsp;"
                    if playlisttrack[7] == "": playlisttrack[7] = "&nbsp;"
                    if playlisttrack[8] == "": playlisttrack[8] = "&nbsp;"
                    if playlisttrack[9] == "": playlisttrack[9] = "&nbsp;"

                    exportFile.write("<TR>")
                    exportFile.write("<TD>" + playlisttrack[0].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[1].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[2].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[3].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[4])  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[5])  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[6].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[7])  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[8].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(datetime.datetime.fromtimestamp(float(int(playlisttrack[9])/1000000))) + "</TD>")
                    exportFile.write("</TR>\n")

          if exportFormat == "HTML":
               exportFile.write(self.HTMLFooter)

          exportFile.close()

          if saveToDropbox == False or saveLocation == "Locally":
               # If this wasn't called from the command line argument, display a message that it has completed
               if isCommandLine == False:
                    self.messageBox("Export Playlist", "The export of the playlist " + playlistName + " has completed")
               else:
                    return
          elif saveToDropbox == True or saveLocation == "Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

               # Write the file to Dropbox
               with open(fileName, 'rb') as output:
                    response = self.dropBoxClient.put_file(fileName, output)

                    output.close()

                    os.remove(fileName)

               if len(sys.argv) == 1:
                    self.messageBox("Export Playlist", "The export of the playlist " + playlistName + " has completed")

     # Export the songs currently being displayed in the recently added window
     def exportRecentlyAdded(self):
          exportFormat=self.promptForSaveFormat()
          
          if exportFormat=="Cancel":
               return
          
          saveLocation = self.promptForSaveLocation()
          
          if saveLocation=="Locally":
               if exportFormat=="CSV":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the recently added file', "", 'CSV (*.csv)')
               else:
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the recently added file', "", 'HTML (*.html)')
               
               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return
          elif saveLocation == "Dropbox":
               fileName = playlistName + "." + exportFormat.lower()
          elif saveLocation == "Cancel":
               return
               
          exportFile = open(fileName, "w")

          csvHeader = "Artist,Album,Track,Track Number,Date Added\n"
          HTMLHeader = "<HTML>\n<HEAD>\n<STYLE>\ntable td {\nborder: 0.5px solid black;\nborder-collapse: collapse;\ncellpadding: 0px;\nbackground-color:#FFFFFF;\ncolor:black;\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1 cellspacing=0>\n<TR><TD>Artist</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Date Added</TD></TR>\n"
          
          # Heading
          if exportFormat == "CSV":
               exportFile.write(csvHeader)
          elif exportFormat == "HTML":
               exportFile.write(HTMLHeader)

          # self.newSongs.append([self.library[currNewSong][3], self.library[currNewSong][2], self.library[currNewSong][1], self.library[currNewSong][4]])
          # Playlist Data
          for song in self.newSongs:
               if exportFormat == "CSV":
                    # All double quotation marks have to be replaced with "" to be parsed correctly as a CSV
                    exportFile.write('"' + song[0].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + song[1].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + song[2].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34)) + '",')
                    exportFile.write('"' + str(song[3]) + '",')
                    exportFile.write('"' + str(song[4]) + '"\n')
               elif exportFormat == "HTML":
                    # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                    if song[0] == "": song[0] = "&nbsp;"
                    if song[1] == "": song[1] = "&nbsp;"
                    if song[2] == "": song[2] = "&nbsp;"
                    if song[3] == "": song[3] = "&nbsp;"
                    if song[4] == "": song[4] = "&nbsp;"

                    exportFile.write("<TR>")
                    exportFile.write("<TD>" + song[0].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + song[1].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + song[2].encode('utf-8').strip().replace(chr(34), chr(34) + chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(song[3]) + "</TD>")
                    exportFile.write("<TD>" + str(song[4]) + "</TD>")
                    exportFile.write("</TR>\n")

          if exportFormat == "HTML":
               exportFile.write(self.HTMLFooter)

          exportFile.close()

          if saveLocation == "Locally":
               self.messageBox("Export Playlist", "The export of the recently added files has completed")
          elif saveToDropbox == True or saveLocation == "Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

               # Write the file to Dropbox
               with open(fileName, 'rb') as output:
                    response = self.dropBoxClient.put_file(fileName, output)

                    output.close()

                    os.remove(fileName)

               if len(sys.argv) == 1:
                    self.messageBox("Export Playlist", "The export of the recently added files has completed")

     # Find duplicate tracks between 2 playlists
     def findDuplicateTracksInPlaylist(self,playlist1,playlist2,isCommandLine=False, saveToDropbox=False, fileName=None):
          playlist1IDs=set()
          playlist2IDs=set()
          
          # Loop through all tracks in playlist1 and add the ID to playlist1IDs set
          for playlist in self.playlists:
               if playlist["name"] == playlist1:
                    for track in sorted(playlist["tracks"]):
                         playlist1IDs.add(track['trackId'])

          # Loop through all tracks in playlist2 and add the ID to playlist2IDs set
          for playlist in self.playlists:
               if playlist["name"] == playlist2:
                    for track in sorted(playlist["tracks"]):
                         playlist2IDs.add(track['trackId'])                         
          
          # Compare the 2 sets and store the results in a new set
          dupes=playlist1IDs.intersection(playlist2IDs)
          
          # When the resulting set is empty there are no duplicates
          if len(dupes) == 0:
               # This function was not run from the command line so display message with MessageBox
               if fileName is None:
                    self.messageBox("Find duplicate tracks in playlists","There were no duplicates found between " + playlist1 + " and " + playlist2)
               else:
                    print "There were no duplicates found between " + playlist1 + " and " + playlist2
               
               return
          
          # If filename wasn't provided, this function was run from the GUI and not the command line
          if isCommandLine == False:               
               # Get the location to save the resulting file (Locally or Dropbox)
               saveLocation = self.promptForSaveLocation()
               
               if saveLocation == "Cancel":
                    return
               
               # Prompt for the file name if the file is being saved locally
               if saveLocation == "Locally":
                    fileName, filter = QtGui.QFileDialog.getSaveFileName(self, 'Choose the location to save the results of the comparison',playlist1 + " to " + playlist2 + " Comparison.csv", 'CSV (*.csv)')
               
                    # If the user clicked on cancel then do nothing
                    if fileName is None or fileName == "":
                         return False
               else:
                    fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
          elif saveToDropbox == True:
               saveLocation="Dropbox"
               fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
          elif saveToDropbox == False:
               saveLocation="Locally"
               fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
                         
          comparisonResults = open(fileName, "w")
          
          comparisonResults.write(self.csvHeader)
          
          # Write the output file
          for id in dupes:
               currTrack = self.library[id]               
               comparisonResults.write('"' + currTrack[0].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write('"' + currTrack[1].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write('"' + currTrack[2].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write('"' + currTrack[3].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write(str(currTrack[4]) + ',')
               comparisonResults.write(str(currTrack[5]) + ',')
               comparisonResults.write('"' + currTrack[6].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write(str(currTrack[7]) + ',')
               comparisonResults.write('"' + currTrack[8].encode('utf-8').strip().replace(chr(34), chr(34)+chr(34)) + '",')
               comparisonResults.write('"' + str(datetime.datetime.fromtimestamp(float(int(currTrack[9])/1000000))) + '"\n')

          comparisonResults.close()

          # Save to Dropbox if that was selected as the save location
          if saveToDropbox == True or saveLocation=="Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

               # Write the file to Dropbox
               with open(fileName, 'rb') as output:
                    response = self.dropBoxClient.put_file(fileName, output)

                    output.close()

               os.remove(fileName)

          if isCommandLine==False:
               self.resetLayout()
          else:
               sys.exit()
               
     # Event when the user clicks on the Export As ComboBox for a library task
     def libraryExportFormatComboBoxChange(self):
          if str(self.libraryTaskComboBox.currentText()) == "Export your entire library" and self.libraryExportFormatComboBox.currentIndex() != 0:
               self.exportLibrary(None, self.libraryExportFormatComboBox.currentText())
               self.resetLayout()

     # Event when the user chooses a library related task
     def libraryTaskComboBoxChange(self, optionItem):
          if optionItem == "Export your entire library":
               # Always hide the recently added date dropdown when this is chosen
               self.recentlyAddedLabel.hide()
               self.recentlyAddedDateEdit.hide()
               
               if self.libraryExportFormatComboBox.isHidden() == False and self.libraryExportFormatComboBox.currentIndex() != 0:
                    self.exportLibrary()
                    self.resetLayout()
               else:
                    self.libraryExportFormatLabel.show()
                    self.libraryExportFormatComboBox.show()
          elif optionItem == "View recently added files":
                    # Hide export format label and dropdown
                    self.libraryExportFormatLabel.hide()
                    self.libraryExportFormatComboBox.hide()
                    
                    self.recentlyAddedLabel.show()
                    self.recentlyAddedDateEdit.show()
          else:
               self.libraryExportFormatLabel.hide()
               self.libraryExportFormatComboBox.hide()

     # Load the library of songs
     def loadLibrary(self):
          # Load library - Get Track ID,Song Title,Album,Artist and Track number for each song in the library
          #
          # We must have a try except here to trap an error since this API call will randomly return a 500 error from Google
          try:
               self.library = {song['id']: [song['id'], song['title'], song['album'], song['artist'], song['trackNumber'], song.get("year", ""), song['albumArtist'], song['discNumber'], song.get("genre", ""), song.get("creationTimestamp","")] for song in self.mc.get_all_songs()}
          except:
               # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
               if len(sys.argv) == 1:
                    self.messageBox("Library Error", "An error occurred while getting the list of songs in your library. Please try again")
               else:
                    print "An error occurred while getting the list of songs in your library. Please try again"
               sys.exit()

     # Load playlists and store values in the playlist ComboBox
     def loadPlaylists(self):
          self.playlists = self.mc.get_all_user_playlist_contents()

          playlistNames = []

          # Add Empty entry into playlist so theres always a blank option at the top
          playlistNames.insert(0, "")

          for playlist in self.playlists:
               playlistNames.insert(0, playlist["name"])

          playlistNames.sort(key=lambda s: s.lower())

          self.playlistComboBox.clear()
          self.playlistComboBox2.clear()
          
          for playlist in playlistNames:
               self.playlistComboBox.addItem(playlist)
               self.playlistComboBox2.addItem(playlist)

     # Display MessageBox with Ok button
     def messageBox(self, title, message):
          QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)

          return True

     # Display MessageBox with Yes/No Buttons
     def messageBox_YesNo(self, title, message):
          reply = QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)

          if reply == QtGui.QMessageBox.Yes:
               return "YES"
          else:
               return "NO"

     # Parse and validate command line arguments
     def parseCommandLineArguments(self):
          validParameter = False

          # Command line arguments are the # of total parameters required including the app
          claParameters = {"/createplaylist" : 3, "/deleteplaylist" : 2, "/downloadplaylist" : 3, "/duplicateplaylist" : 3, "/exportplaylist": 4, "/exportallplaylists":3, "/exportlibrary":3,"/findduplicates":4,"/help": 1, "/recentlyadded":4, "/renameplaylist":3}

          # No command line arguments
          if len(sys.argv) <= 1:
               # Load all playlists
               self.playlists = self.mc.get_all_user_playlist_contents()

               self.loadLibrary()

               return

          # Verify that the correct # of parameters were given. I start at index 1 and not 0 because index 0 referes to this script
          validParameter = False

          # loop through all parameters
          for key in claParameters:
               if key == sys.argv[1]:
                    validParameter = True

                    # If the # of arguments is not correct for this parameter, display an error
                    if len(sys.argv)-1 != claParameters[key]:
                         print "Invalid number of command line parameter(s) given for " + sys.argv[1]
                         self.commandLineUsage()
                         sys.exit()

          # If the parameter isn't valid
          if validParameter == False:
               print "Invalid command line parameter(s) " + sys.argv[1]
               self.commandLineUsage()
               sys.exit()

          if sys.argv[1] == '/help' or sys.argv[1] ==  "/?":
               self.commandLineUsage()
          elif sys.argv[1] == "/createplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2] and AllowDuplicatePlaylistNames == False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         self.commandLineUsage()
                         sys.exit()
               if str(sys.argv[3])[-4:].upper() != ".CSV":
                    print "The filename argument for /createplaylist must be a CSV file"
                    self.commandLineUsage()
                    sys.exit()
               self.createPlaylistFromCSV(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/deleteplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    sys.exit()

               self.deletePlaylist(sys.argv[2])
          elif sys.argv[1] == "/downloadplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    sys.exit()

               self.loadLibrary()

               if sys.argv[3] == "Dropbox":
                    self.downloadPlaylistToDirectory(sys.argv[2], None, True)
               else:
                    self.downloadPlaylistToDirectory(sys.argv[2], sys.argv[3])

               sys.exit()
          elif sys.argv[1] == "/duplicateplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3] and AllowDuplicatePlaylistNames == False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/exportlibrary":
               # Convert the export format to upper case
               sys.argv[3] = sys.argv[3].upper()

               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print "The export format " + sys.argv[3] + " is not valid."
                    sys.exit()

               if sys.argv[2] == "Dropbox":
                    self.exportLibrary(None, sys.argv[3], True)
               else:
                    self.exportLibrary(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/exportplaylist":
               # Convert the export format to upper case
               sys.argv[4] = sys.argv[4].upper()
               
               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print "The export format " + sys.argv[4] + " is not valid."
                    sys.exit()
               self.playlists = self.mc.get_all_user_playlist_contents()

               self.loadLibrary()

               # Validate that the playlist is a valid one
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this Google account"
                    sys.exit()

               if sys.argv[3] == "Dropbox":
                    self.exportPlaylist(sys.argv[2], None, sys.argv[4], True)
               else:
                    self.exportPlaylist(sys.argv[2], sys.argv[3], sys.argv[4])
          elif sys.argv[1] == "/exportallplaylists":
               # Convert the export format to upper case
               sys.argv[3] = sys.argv[3].upper()

               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print "The export format " + sys.argv[3] + " is not valid."
                    sys.exit()

               self.playlists = self.mc.get_all_user_playlist_contents()

               self.loadLibrary()

               if sys.argv[2] == "Dropbox":
                    self.exportAllPlaylists(None, sys.argv[3], True)
               else:
                    self.exportAllPlaylists(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/findduplicates":
               # Validate that both playlists are valid ones`
               
               # First playlist argument
               validPlaylist = False
               
               self.playlists = self.mc.get_all_user_playlist_contents()

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this Google account"
                    sys.exit()

               # Second playlist
               validPlaylist = False
               
               self.playlists = self.mc.get_all_user_playlist_contents()

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[3] + " is not a valid playlist name for this Google account"
                    sys.exit()

               # We need to load the library because we have to get all of the track information
               self.loadLibrary()
               
               if sys.argv[4] == "Dropbox":
                    self.findDuplicateTracksInPlaylist(sys.argv[2], sys.argv[3],True,True)
               else:
                    self.findDuplicateTracksInPlaylist(sys.argv[2], sys.argv[3], True,False,sys.argv[4])
          elif sys.argv[1] == "/recentlyadded":
               # Convert the export format to upper case
               sys.argv[4] = sys.argv[4].upper()

               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print "The export format " + sys.argv[4] + " is not valid."
                    sys.exit()

               try:
                    # This will raise ValueError if sys.argv[2] is not a valid date
                    asofDate = datetime.datetime.strptime(sys.argv[2], '%m/%d/%Y')
                    asofDate = asofDate.date()

                    # Load library
                    self.loadLibrary()

                    # Call buildRecentlyAddedWindow() to save the file
                    if sys.argv[3] == "Dropbox":
                          self.buildRecentlyAddedWindow(asofDate, None, sys.argv[4], True)
                    else:
                         self.buildRecentlyAddedWindow(asofDate, sys.argv[3], sys.argv[4])
               except ValueError:
                    print "The recently added date " + sys.argv[2] + " is not valid"
                    sys.exit()
          elif sys.argv[1] == "/renameplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3] and AllowDuplicatePlaylistNames == False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2], sys.argv[3], True)

          sys.exit()

     # Perform Dropbox authentication so we can read and write to it
     def performDropboxOAuth(self):
          dropBoxFilename = "DropboxOauth.cred"

          # If the Dropbox oauth access code file doesn't exist, initiate the Oauth process through Dropbox
          if os.path.isfile(dropBoxFilename) == False:
               skey = '#&G%F$G&DJ()!%&D'
               cipher = AES.new(skey,AES.MODE_ECB) # never use ECB in strong systems obviously
               decoded = cipher.decrypt(base64.b64decode("5zJ63Um/u9FYNpzWObCPwPDp4O9bjRRWaBoItzULMao="))
               
               appk = decoded.strip()
               
               decoded = cipher.decrypt(base64.b64decode("5zJ63Um/u9FYNpzWObCPwLb/Pwd2b94nHW/5KhcbhOU="))
               apps = decoded.strip()

               flow = dropbox.client.DropboxOAuth2FlowNoRedirect(appk,apps)

               authorize_url = flow.start()

               # Allow OAuth prompt to be displayed in console
               if len(sys.argv) == 1:
                    self.messageBox("Dropbox OAuth", "When you click on OK, this script will open a web browser window asking you to allow GMusicUtility to connect to your Dropbox account (you might have to log in first). Please click on Allow and copy the authorization code into the command prompt window")
                    webbrowser.open(authorize_url)
               else:
                    print "Please log into DropbBox in your browser and then visit the URL " + authorize_url + ". After allowing Google Play Music Utility, paste the code here."

               code = raw_input("Enter the authorization code here: ").strip()

               # This will fail if the user enters an invalid authorization code
               try:
                    access_token = flow.finish(code)
               except dbrest.ErrorResponse, e:
                    print 'Error: %s' % (e,)
                    return False

               dbaccess = open(dropBoxFilename, "w")
               dbaccess.write(access_token)
               dbaccess.close()
          else:
               dbaccess = open(dropBoxFilename, "r")
               access_token = dbaccess.readline()
               dbaccess.close()

          try:
               self.dropBoxClient = dropbox.client.DropboxClient(access_token)
          except:
               if len(sys.argv) == 1:
                    self.messageBox("Dropbox authentication failed", "Your Dropbox authentication has failed. Please make sure that you entered a valid code.")
               else:
                    print "Your Dropbox authentication has failed. Please make sure that you entered a valid code."

               return False

     # Perform Google OAuth authentication because we need to use OAuth when using the Musicmanager interface
     def performGoogleOAuth(self):
          # In order to use the Musicmanager interface, we have to authenticate with Google using OAuth2. Once OAuth has been completed it will
          # create a file in the current directory called GoogleOAuth.cred. If this file already exists, we don't need to go through the OAuth
          # process again
          if os.path.isfile("GoogleOAuth.cred") == False:
               try:
                    self.mm.perform_oauth("GoogleOAuth.cred", True)
               except:
                    if len(sys.argv) == 1:
                         self.messageBox("Google Play Music authentication failed", "Your Google Play Music authentication has failed. Please make sure that you entered a valid code.")
                    else:
                         print "Your Google Play Music authentication has failed. Please make sure that you entered a valid code."
                         return False
          try:
               # Login using GoogleOAuth.cred
               self.mm.login("GoogleOAuth.cred")
          except AlreadyLoggedIn:
               return True
          except:
               return False

     # Event when the user chooses an item from the playlist ComboBox
     def playlistComboBoxChange(self):
          # These playlist tasks don't require the user to pick the export format
          if str(self.playlistTaskComboBox.currentText()) == "Delete a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.deletePlaylist(str(self.playlistComboBox.currentText()), True)

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Duplicate a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.duplicatePlaylist(str(self.playlistComboBox.currentText()))

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Reorder a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.buildReorderPlaylistWindow(str(self.playlistComboBox.currentText()))

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Rename a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.duplicatePlaylist(str(self.playlistComboBox.currentText()), None, True)

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Download all songs in a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.downloadPlaylistToDirectory(str(self.playlistComboBox.currentText()))

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Find duplicates tracks in playlists":
               # If either or both playlist dropdowns don't have a playlist selected do nothing
               if self.playlistComboBox.currentText() == "" or self.playlistComboBox2.currentText() == "":
                    return
               
               # If both playlist dropdowns have a playlist selected and they are the same playlist
               if self.playlistComboBox.currentText() == self.playlistComboBox2.currentText():
                    self.messageBox("Find duplicates tracks in playlists","You cannot compare a playlist to itself. Please select 2 different playlists to compare")
                    
                    # Clear the value of the last selected playlist based on which object triggered this event
                    if self.sender().objectName()=="playlistComboBox":
                         self.playlistComboBox.setCurrentIndex(-1)
                    else:
                         self.playlistComboBox2.setCurrentIndex(-1)

                    return
               else:
                    self.findDuplicateTracksInPlaylist(self.playlistComboBox.currentText(),self.playlistComboBox2.currentText())
          else:
               # If the Playlist Export Format is already selected, trigger the event
               if self.playlistExportFormatComboBox.isHidden() == False and self.playlistExportFormatComboBox.currentIndex() != -1:
                    if str(self.playlistTaskComboBox.currentText()) == "Export a playlist":
                         # If export format is not selected exit 
                         if self.playlistExportFormatComboBox.currentIndex() == -1 or self.playlistExportFormatComboBox.currentIndex() == 0:
                              return
                              
                         self.exportPlaylist(playlistName=str(self.playlistComboBox.currentText()), exportFormat=self.playlistExportFormatComboBox.currentText())

                         self.resetLayout()
                         return
                    elif  str(self.playlistTaskComboBox.currentText()) == "Export all playlists":
                         self.exportAllPlaylists(None, self.playlistExportFormatComboBox.currentText())

                         self.resetLayout()
                    return

     # Event when the user clicks on a format to export to
     def playlistExportFormatComboBoxChange(self):
          if str(self.playlistTaskComboBox.currentText()) == "Export a playlist":
               # If no playlist is selected, do nothing
               if self.playlistComboBox.currentIndex() == -1 or self.playlistComboBox.currentIndex() == 0:
                    return

               self.exportPlaylist(str(self.playlistComboBox.currentText()), None, str(self.playlistExportFormatComboBox.currentText()))

               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Export all playlists":
               self.exportAllPlaylists(None, str(self.playlistExportFormatComboBox.currentText()))

               # Reset the layout
               self.resetLayout()

     # Event when the user chooses a playlist related task
     def playlistTaskComboBoxChange(self, optionItem):
          # If Delete a Playlist,Download all songs in a playlist,Duplicate a Playlist or Export a Playlist is selected,show the playlist ComboBox and wait for the user to select a playlist
          # The only exception is Export all playlists which requires that the user only select the export format
          if optionItem == "Delete a playlist" or optionItem == "Download all songs in a playlist" or optionItem == "Duplicate a playlist" or optionItem == "Export a playlist" or optionItem == "Reorder a playlist" or optionItem == "Rename a playlist" or optionItem == "Find duplicates tracks in playlists":
		     # Only this option from the ones above require the export format to be shown
               if optionItem == "Export a playlist":
                    self.playlistComboBox.show()
                    self.playlistExportFormatLabel.show()

                    # unset and show Export as ComboBox
                    if optionItem != "Download all songs in a playlist":
                         self.playlistExportFormatComboBox.setCurrentIndex(-1)
                         self.playlistExportFormatComboBox.show()
               else:
                    self.playlistExportFormatComboBox.hide()
                    self.playlistExportFormatLabel.hide()
               
               # When this option is selected, we modify the label
               if optionItem == "Find duplicates tracks in playlists":
                    self.playlistLabel.setText("1st Playlist")
                    self.playlistLabel2.show()
                    self.playlistComboBox2.show()
                    
               self.playlistLabel.show()
               self.playlistComboBox.show()

               return
          elif optionItem == "Export all playlists":
               self.playlistLabel.hide()
               self.playlistComboBox.hide()

               self.playlistExportFormatComboBox.show()
               self.playlistExportFormatLabel.show()

               # self.exportAllPlaylists()
               #self.resetLayout()

               return
          elif optionItem == "Create a playlist from CSV":
               self.createPlaylistFromCSV()
               self.loadPlaylists()

               self.resetLayout()
          else: # Nothing selected
               self.resetLayout()

     # Dialog to prompt for the save location (Currently locally or Dropbox)
     def promptForSaveFormat(self):
          # This function returns "CSV" , "HTML" or "Cancel"

          # Create custom dialog to prompt user where to save the playlist
          custDialog = QtGui.QMessageBox()
          custDialog.setText("Please choose the export format")
          custDialog.setWindowTitle("Export Format")
          custDialog.addButton(self.tr("CSV"), QMessageBox.YesRole)
          custDialog.addButton(self.tr("HTML"), QMessageBox.NoRole)
          custDialog.addButton(self.tr("Cancel"), QMessageBox.RejectRole)
          ret = custDialog.exec_()

          if ret == 0:
               return "CSV"
          elif ret == 1:
               return "HTML"
          elif ret == 2:
               return "Cancel"
               
     # Dialog to prompt for the save location (Currently locally or Dropbox)
     def promptForSaveLocation(self):
          # This function returns "Locally" , "Dropbox" or "Cancel"

          # Create custom dialog to prompt user where to save the playlist
          custDialog = QtGui.QMessageBox()
          custDialog.setText("Do you want to save the file locally or to Dropbox ?")
          custDialog.setWindowTitle("Save location")
          custDialog.addButton(self.tr("Locally"), QMessageBox.YesRole)
          custDialog.addButton(self.tr("Dropbox"), QMessageBox.NoRole)
          custDialog.addButton(self.tr("Cancel"), QMessageBox.RejectRole)
          ret = custDialog.exec_()

          if ret == 0:
               return "Locally"
          elif ret == 1:
               return "Dropbox"
          elif ret == 2:
               return "Cancel"

     # Event when the user selects a date in the recently added widget
     def recentlyAddedDateEditChange(self):
          # Use the values stored from the QDateEdit
          self.recentlyAddedYear = self.recentlyAddedDateEdit.date().year()

          self.recentlyAddedMonth = self.recentlyAddedDateEdit.date().month()

          self.recentlyAddedDay = self.recentlyAddedDateEdit.date().day()

          # Reset the As of Label and QDateEdit controls after a date has been selected
          self.recentlyAddedLabel.hide()

          self.recentlyAddedDateEdit.hide()

          self.libraryTaskComboBox.setCurrentIndex(-1)

          # Display the window with the table
          self.buildRecentlyAddedWindow()

          return True

     # Event when the user enters a date into recently added using the keyboard
     def recentlyAddedDateEditKeypress(self):
          # Disable keyboard events since this event is automatically triggered as soon as the date changes even when the user hasn't finished entering a date
          PySide.QtCore.QEvent.ignore()

     # Reset the layout of the window
     def resetLayout(self):
          self.playlistTaskComboBox.setCurrentIndex(-1)

          # When the user selects "Find duplicates tracks in playlists", we modify the playlist label to 1st Playlist. This will always restore it to its original value
          self.playlistLabel.setText("Playlist")
          
          self.playlistLabel.hide()
          self.playlistComboBox.setCurrentIndex(-1)
          self.playlistComboBox.hide()
          self.playlistExportFormatLabel.hide()
          self.playlistExportFormatComboBox.setCurrentIndex(-1)
          self.playlistExportFormatComboBox.hide()

          self.libraryExportFormatLabel.hide()
          self.libraryExportFormatComboBox.hide()
          self.recentlyAddedDateEdit.hide()
          self.recentlyAddedLabel.hide()

          self.libraryTaskComboBox.setCurrentIndex(-1)
          self.libraryExportFormatComboBox.setCurrentIndex(-1)

          self.playlistLabel2.hide()
          self.playlistComboBox2.setCurrentIndex(-1)
          self.playlistComboBox2.hide()
          
     # Prompt the user and return the result
     def showDialog(self, title, promptText):
          # the result of user input. It is "" when user clicks on ok without entering anything or None when they cancel the dialog
          result = None

          text, ok = QtGui.QInputDialog.getText(self, title, promptText)

          if ok:
               return str(text)
          else:
               return None

app = QtGui.QApplication(sys.argv)

# If either one is blank or set to the defaults, display login prompt
if username is None or username == "mygmailaddress@gmail.com" or password is None or password == "mypassword":
     # If the user specifies /help as a command line argument, display the usage without worrying if the login credentials are stored
     if len(sys.argv) == 2 and (sys.argv[1] == "/help" or sys.argv[1] == "/?"):
         # The command line usage function is a part of the GMusicUtility class. I pass an empty string and bypass the login in the init if /help is specified as a command lineargument
         gMusicUtility = GMusicUtility("", "")
         sys.exit()

     # When login credentials aren't stored or set to defaults and command line arguments are being used, do not display login
     if len(sys.argv) > 1:
          print "Error: The login information is not stored. Please edit this script with your login information if you want to use command line arguments"
          sys.exit()

     l = Login()

     if l.exec_() == QtGui.QDialog.Accepted:
          auth = l.getCreds()

          gMusicUtility = GMusicUtility(auth[0], auth[1])
else:
     gMusicUtility = GMusicUtility(username, password)

sys.exit(app.exec_())