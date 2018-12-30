import base64
import csv
import datetime
import dropbox
import hashlib
import logging
import operator
import os
import os.path
import pyaes
import random
import re
import string
import sys
import tempfile
import time
import urllib3
import requests
import webbrowser
from datetime import date, timedelta
from dropbox import DropboxOAuth2FlowNoRedirect
from functools import partial
from requests.adapters import HTTPAdapter
from gmusicapi import Mobileclient
from gmusicapi import Musicmanager
from gmusicapi.exceptions import AlreadyLoggedIn
from PySide2.QtWidgets import QApplication, QComboBox, QDateEdit, QFileDialog, QInputDialog, QLabel, QMessageBox, QPushButton, QTableView, QTableWidget,QVBoxLayout, QWidget 
from PySide2 import QtCore
from PySide2.QtCore import *
from PySide2.QtGui import QFont
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from slugify import slugify
from time import gmtime, strftime

# To Do
# -----
# See if you can make reorder playlist work. Drag and drop doesn't work correctly

# Changes
# -------

checkForUpdates = True

tableForegroundColor = None

tableBackgroundColor = None

# Change this to True if you want to allow duplicate playlist names (not recommended because it can cause problems)
AllowDuplicatePlaylistNames = False

# change this to True if you do not want an m3u file to be created when you use the Download All Songs in a Playlist feature
noM3U=False

# Change this to True if you do not want to create Artist and Album folders when downloading all songs in a playlist
noSubDirectories=False

### DO NOT EDIT ANYTHING BELOW THIS LINE
urllib3.disable_warnings()

# Fix for the error NotImplementedError: resource_filename() only supported for .egg, not .zip which is related to Dropbox API
# http://mfctips.com/2013/05/03/dropbox-python-sdk-with-py2exe-causes-notimplementederror-resource_filename-only-supported-for-egg-not-zip/
#
# Generate m3u playlist from a directory
# https://gist.github.com/jonlabelle/6098281

# This is an SSL patch found at http://stackoverflow.com/questions/24973326/requests-exceptions-sslerror-errno-185090050 to force this script to use the local cacert.pem. This is needed when compiling this script into an exe using py2exe because otherwise the executable will throw an SSL error due to not finding the SSL certificate
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
        #print "moveRows called, self.data = %s" % self.data
        self.beginMoveRows(parent, source_first, source_last, parent2, dest)

        self.data = self.data[1] + self.data[0] + self.data[2]
        self.endMoveRows()
        #print "moveRows finished, self.data = %s" % self.data
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

class TableSwitcher(QTableWidget):
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
        self.setItem(src_row, src_col, QTableWidgetItem(dest_value))

class GMusicUtility(QWidget):
     mc = None # Mobileclient interface

     mm = None # Musicmanager interface

     dropBoxClient = None # Dropbox interface

     # playlist header used on all exports
     csvHeader = ["Track ID","Track Name","Album","Artist","Track Number","Year","Album Artist","Disc Number","Genre"]

     # HTML header used on all exports
     HTMLHeader = None

     # HTML Footer used on all exports
     HTMLFooter = "</TABLE>" + os.linesep + "</BODY>" + os.linesep + "</HTML>"

     playlists = None

     library = None

     siteURL="https://github.com/SegiH/gmusicutility"

     # App Version - Used to check for updates
     version = "4.2"

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

     updateLabel = None

     table_view = None

     recentlyAddedLayout = None

     recentlyAddedYear = 0

     recentlyAddedMonth = 0

     recentlyAddedDay = 0
 
     salt="VpNbhrDhgWRjpLzyaZIShmPqu"

     newSongs=None

     # Window width & height
     width = 850
     height = 150

     # Coordinates for the controls for each column (X coordinate)
     columnXCoordinates = [15, 275, 530]

     # Coordinates for the controls for each row (Y coordinate)
     rowYCoordinates = [20, 40, 80, 100]

     validFormats = ["CSV", "HTML"]
     
     delimiter=None
	 
     GoogleOAuthCredFile="GoogleOAuth.cred"
     
     GoogleMMOAuthCredFile="GoogleOAuth-mm.cred"
          
     def __init__(self):
          super(GMusicUtility, self).__init__()

          # If the user wants to see the command line usage, call commandLineUsage() and exit without authenticating
          if len(sys.argv) > 1 and (sys.argv[1] == "/help" or sys.argv[1] == "/?"):
               if len(sys.argv) > 2 and not sys.argv[2] is None:
                    self.commandLineUsage(sys.argv[2])
               else:
                    self.commandLineUsage()

               sys.exit()

          # Set the global delimiter
          if sys.platform == "win32":
               self.delimiter = "\\"
          else:
               self.delimiter = "/"

          self.mc = Mobileclient()

          # We have to use the Musicmanager interface to download music
          self.mm = Musicmanager()

          # Supress insecure warnings
          logging.captureWarnings(True)
          
          if os.path.isfile(self.GoogleOAuthCredFile) == False:
               try:
                    self.mc.perform_oauth(self.GoogleOAuthCredFile, True)
               except:
                    if len(sys.argv) == 1:
                         self.messageBox("Google Play Music authentication failed", "Your Google Play Music authentication has failed. Please make sure that you entered a valid code.")
                         return False                         
                    else:
                         print("Your Google Play Music authentication has failed. Please make sure that you entered a valid code.")
                         return False                     
          else: # Log in using existing OAuth
               try:
                    errorMessage="Unable to complete OAuth with your Google account. Please try again."

                    # Login using GoogleOAuth.cred
                    if self.mc.oauth_login(Mobileclient.FROM_MAC_ADDRESS,self.GoogleOAuthCredFile) == False:
                         # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
                         if len(sys.argv) == 1:
                              self.messageBox("Google Play Music Utility", errorMessage)
                              sys.exit()
                         else:
                              print(errorMessage)
                              sys.exit()
               except AlreadyLoggedIn:
                    pass
               except Exception as e:
                    if len(sys.argv) == 1:
                         self.messageBox("Google Play Music Utility", errorMessage)
                         print(e)
                         sys.exit()
                    else:
                         print(errorMessage)
                         print(e)
                         sys.exit()

          if tableForegroundColor is None or tableBackgroundColor is None:
               # Default
               self.HTMLHeader = "<HTML>" + os.linesep + "<HEAD>" + os.linesep + "<STYLE>" + os.linesep + "table td {" + os.linesep + "border: 0.5px solid black;" + os.linesep + "border-collapse: collapse;" + os.linesep + "cellpadding: 0px;" + os.linesep + "background-color:#FFFFFF;" + os.linesep + "color:black;" + os.linesep + "}" + os.linesep + "</STYLE>" + os.linesep + "<HEAD>" + os.linesep + "<BODY>" + os.linesep + "<TABLE BORDER=1 cellspacing=0>" + os.linesep + "<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD></TR>" + os.linesep
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

               self.HTMLHeader = "<HTML>" + os.linesep + "<HEAD>" + os.linesep + "<STYLE>" + os.linesep + "table td {" + os.linesep + "     border-style: solid;" + os.linesep + "    border-width: 0px;" + os.linesep + "    border-color:red;" + os.linesep + "    background-color:" + str(tableBackgroundColor) + ";" + os.linesep + "    color:" + str(tableBackgroundColor) + ";" + os.linesep + "}" + os.linesep + "</STYLE>" + os.linesep + "<BODY>" + os.linesep + "<TABLE BORDER=1>" + os.linesep + "<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD></TR>" + os.linesep
          
          self.parseCommandLineArguments()
  
          self.buildMainWindow()

          # Check for updates
          if checkForUpdates == True:
               self.checkForUpdate()

     # Build the main screen
     def buildMainWindow(self):
          self.resize(self.width, self.height)
          self.setWindowTitle('Google Play Music Utility ' + self.version + " Written by Segi Hovav")

          leftPadding = 45

          ### Column 1 ###

          # Playlist Task Options Label
          self.playlistTaskLabel = QLabel(self)
          self.playlistTaskLabel.setText("Playlist Options")
          self.playlistTaskLabel.move(self.columnXCoordinates[0], self.rowYCoordinates[0])

          # Playlist Task ComboBox
          self.playlistTaskComboBox = QComboBox(self)
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
          self.libraryTaskLabel = QLabel(self)
          self.libraryTaskLabel.setText("Library Options")
          self.libraryTaskLabel.move(self.columnXCoordinates[0], self.rowYCoordinates[2])

          # Library Task ComboBox
          self.libraryTaskComboBox = QComboBox(self)
          self.libraryTaskComboBox.addItem(None)
          self.libraryTaskComboBox.addItem("Export all purchased songs")
          self.libraryTaskComboBox.addItem("Export your entire library")
          self.libraryTaskComboBox.addItem("View recently added files")
          self.libraryTaskComboBox.activated[str].connect(self.libraryTaskComboBoxChange)
          self.libraryTaskComboBox.move(self.columnXCoordinates[0], self.rowYCoordinates[3])

          ### Column 2 ###

          # Playlist Label
          self.playlistLabel = QLabel(self)
          self.playlistLabel.setText("Playlist")
          self.playlistLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[0])
          self.playlistLabel.hide()

          # Playlist ComboBox
          self.playlistComboBox = QComboBox(self)
          self.playlistComboBox.setObjectName("playlistComboBox") # Set the playlist combobox name so we can use it for validation when comparing 2 playlists
          self.playlistComboBox.move(self.columnXCoordinates[2]+(leftPadding), self.rowYCoordinates[0])
          self.playlistComboBox.activated[str].connect(self.playlistComboBoxChange)

          # Library Export Format Label
          self.libraryExportFormatLabel = QLabel(self)
          self.libraryExportFormatLabel.setText("Export as")

          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.libraryExportFormatLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[2])
          self.libraryExportFormatLabel.hide()

          # Library Export Format ComboBox
          self.libraryExportFormatComboBox = QComboBox(self)
          self.libraryExportFormatComboBox.addItem(None)
          self.libraryExportFormatComboBox.addItem("CSV")
          self.libraryExportFormatComboBox.addItem("HTML")
          self.libraryExportFormatComboBox.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[3])
          self.libraryExportFormatComboBox.activated[str].connect(self.libraryExportFormatComboBoxChange)
          self.libraryExportFormatComboBox.hide()

          # Recently Added Label
          self.recentlyAddedLabel = QLabel(self)
          self.recentlyAddedLabel.setText("Added since")

          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.recentlyAddedLabel.move(self.columnXCoordinates[1]+leftPadding, self.rowYCoordinates[2])
          self.recentlyAddedLabel.hide()

          # Recently Added ComboBox
          self.recentlyAddedDateEdit = QDateEdit(self)
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
          self.playlistExportFormatLabel = QLabel(self)
          self.playlistExportFormatLabel.setText("Export as")

          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatLabel.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[0])
          self.playlistExportFormatLabel.hide()

          # Export Format ComboBox
          self.playlistExportFormatComboBox = QComboBox(self)
          self.playlistExportFormatComboBox.addItem(None)
          self.playlistExportFormatComboBox.addItem("CSV")
          self.playlistExportFormatComboBox.addItem("HTML")
          self.playlistExportFormatComboBox.hide()

          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatComboBox.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[1])
          self.playlistExportFormatComboBox.activated[str].connect(self.playlistExportFormatComboBoxChange)
          
          # Playlist Label for 2nd playlist
          self.playlistLabel2 = QLabel(self)
          self.playlistLabel2.setText("2nd Playlist")
          self.playlistLabel2.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2), self.rowYCoordinates[0])
          self.playlistLabel2.hide()

          # Playlist ComboBox for 2nd playlist
          self.playlistComboBox2 = QComboBox(self)
          self.playlistComboBox2.setObjectName("playlistComboBox2") # Set the playlist combobox name so we can use it for validation when comparing 2 playlists
          
          self.playlistComboBox2.activated[str].connect(self.playlistComboBoxChange)
          self.playlistComboBox2.hide()
          
          # Update available
          self.updateButton = QPushButton(self)
          self.updateButton.setStyleSheet("QPushButton { color : darkred; }");
          self.updateButton.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2)+80,10)
          self.updateButton.resize(200,30)
          self.updateButton.clicked.connect(self.downloadUpdate)
          self.updateButton.hide()

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
                    print("Recently Added: Invalid exportFormat type " + exportFormat)
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
               if float(self.library[currNewSong][9]) > asofDateMS:
                    self.newSongs.append(self.library[currNewSong])
                    '''# if we are exporting to CSV, get all available columns from self.library
                    if fileName is not None:
                         self.newSongs.append([self.library[currNewSong][0], self.library[currNewSong][1], self.library[currNewSong][2], self.library[currNewSong][3], self.library[currNewSong][4], self.library[currNewSong][5], self.library[currNewSong][6], self.library[currNewSong][7], self.library[currNewSong][8]])
                    else:
                         # Otherwise, only add Artist,Album,Track,Track Number and Date Added
                         self.newSongs.append([self.library[currNewSong][3], self.library[currNewSong][2], self.library[currNewSong][1], self.library[currNewSong][4],str(datetime.datetime.fromtimestamp(float(int(self.library[currNewSong][9])/1000000)))])
                    '''
                              
          # When we are saving to Dropbox from the command line, create a default file name since one won't be provided
          if fileName is None:
                    fileName = "RecentlyAdded as of " + time.strftime("%x %X").replace("/", "-") + "." + exportFormat.lower()

          # Sort by Artist (Index 1)
          self.newSongs = sorted(self.newSongs, key=lambda newsong: newsong[0], reverse=True)

          if len(self.newSongs) == 0:
               # If asOf is None, this function was not called from the command line
               if asOf is None:
                    self.messageBox("Recently Added", "There were no songs added since the specified date")
               else:
                    print("There were no songs added since the specified date")
               return

          # When command line arguments were provided use them here
          if asOf is not None:
               self.exportRecentlyAdded(fileName, exportFormat, saveToDropbox)
   
               if fileName is not None:
                    if saveToDropbox == True:
                         # Log into Dropbox using OAuth so we can read and write to it
                         if self.performDropboxOAuth() == False:
                              return

                         # Write the file to Dropbox
                         dest_path = os.path.join('/', fileName)
               
                         with open(fileName,'rb') as f:
                              self.dropBoxClient.files_upload(f.read(),dest_path)

                    sys.exit()

          self.recentlyAddedWidget = QWidget()
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
          self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
          self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
          '''

          self.recentlyAddedLayout = QVBoxLayout(self.recentlyAddedWidget)
          
          self.buttonExportRecentlyAdded = QPushButton('Export Results')
          self.buttonExportRecentlyAdded.clicked.connect(partial(self.exportRecentlyAdded,fileName, exportFormat, saveToDropbox))
          self.recentlyAddedLayout.addWidget(self.buttonExportRecentlyAdded)
          
          self.recentlyAddedLayout.addWidget(self.table_view)
          self.recentlyAddedWidget.setLayout(self.recentlyAddedLayout)

          if self.recentlyAddedYear == 0:
               self.recentlyAddedWidget.show()

     # Check FireBase for latest version
     def checkForUpdate(self):
          latestVersion=requests.get("https://gMusicUtility.firebaseio.com/Version.json").json()

          if str(latestVersion) != str(self.version):
               if len(sys.argv) == 1:
                    self.updateButton.setText("gMusicUtility " + str(latestVersion) + " is available")
                    self.updateButton.show()
               else:
                    print("There is an update available for gMusicUtility: Your version: " + str(self.version) + " latest version: " + str(latestVersion) + ". Please visit " + self.siteURL + " to get the latest version")
          else:
               if len(sys.argv) == 1:
                    self.updateButton.setText("gMusicUtility is up to date.")
                    self.updateButton.show()
               else:
                    print("gMusicUtility is up to date. Current Version is " + self.version)

     # Command line parameters
     def commandLineUsage(self,param=None):
          print (os.linesep)
          print ("Google Play Music Utility command line usage:")
          print (os.linesep)

          if param is None or param == "/checkforupdates":
               print (chr(9) +"/checkforupdates : Check the server for an update to gMusicUtility")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /checkforupdates")
               print (chr(9) + chr(9) + "Prints out message telling you if an update is available and provides a link to get the latest version")
               print (os.linesep)			   

               if param is not None:
                    return

          if param is None or param == "/createplaylist":
               print (chr(9) +"/createplaylist : Create playlist from CSV.")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /createplaylist playlistname filename.csv")
               print (chr(9) + chr(9) + "Ex: " + sys.argv[0] + " /createplaylist Rock Rock.csv")
               print (os.linesep)			   

               if param is not None:
                    return
					
          if param is None or param == "/deleteplaylist":
               print (chr(9) + "/deleteplaylist: Delete a playlist. Use with caution since there's no confirmation when using this.") 
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /deleteplaylist playlistname")
               print (chr(9) + chr(9) + "Ex: " + sys.argv[0] + " /deleteplaylist Rock")
               print (os.linesep)

               if param is not None:
                    return
		
          if param is None or param == "/downloadplaylist":
               print (chr(9) + "/downloadplaylist: Download all songs in a playlist.")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /downloadplaylist playlistname path")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /downloadplaylist Rock c:\playlists")
               print (chr(9) + chr(9) + "Save to DropBox: " + sys.argv[0] + " /downloadplaylist Rock Dropbox")
               print (os.linesep)

               if param is not None:
                    return

          if param is None or param == "/duplicateplaylist":
               print (chr(9) + "/duplicateplaylist: Duplicate a playlist.")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /duplicateplaylist playlistname newplaylistname")
               print (chr(9) + chr(9) + "Ex: " + sys.argv[0] + " /duplicateplaylist Rock Rock2")
               print (os.linesep)

               if param is not None:
                    return
					
          if param is None or param == "/duplicateplaylist":
               print (chr(9) + "/exportplaylist: Export a playlist as CSV or HTML")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /exportplaylist playlistname path format where format is CSV or HTML")
               print (chr(9) + chr(9) + "Save Locally: " + sys.argv[0] + " /exportplaylist Rock c:\RockPlaylist.csv CSV")
               print (chr(9) + chr(9) + "Save to DropBox: " + sys.argv[0] + " /exportplaylist Rock Dropbox CSV")
               print (os.linesep)

               if param is not None:
                    return

          if param is None or param == "/exportallplaylists":
               print (chr(9) + "/exportallplaylists: Export all playlists as CSV or HTML")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /exportallplaylists path format where format is CSV or HTML")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /exportallplaylists c:\playlists CSV")
               print (chr(9) + chr(9) + "Save to DropBox: " + sys.argv[0] + " /exportallplaylists Dropbox CSV")
               print (os.linesep)

               if param is not None:
                    return
		
          if param is None or param == "/exportlibrary":
               print (chr(9) + "/exportlibrary: Export all songs in GPM library as CSV or HTML")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /exportlibrary filename format where format is CSV or HTML")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /exportlibrary c:\MyLibrary.csv CSV")
               print (chr(9) + chr(9) + "Save DropBox: " + sys.argv[0] + " /exportlibrary Dropbox CSV")
               print (os.linesep)

               if param is not None:
                    return

          if param is None or param == "/exportpurchasedsongs":
               print (chr(9) + "/exportpurchasedsongs: Export all purchased songs in GPM library as CSV or HTML")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /exportpurchasedsongs filename format where format is CSV or HTML")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /exportpurchasedsongs c:\PurchasedSongs.csv CSV")
               print (chr(9) + chr(9) + "Save DropBox: " + sys.argv[0] + " /exportpurchasedsongs Dropbox CSV")
               print (os.linesep)

               if param is not None:
                    return

          if param is None or param == "/findduplicates":
               print (chr(9) + "/findduplicates: Compare 2 playlists & find tracks that are in both playlists. Results are saved as CSV automatically")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /findduplicates playlist1 playlist2 format")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /findduplicates Rock Misc Rock_Misc_Comparison.csv")
               print (chr(9) + chr(9) + "Save DropBox: " + sys.argv[0] + " /findduplicates Rock Misc Dropbox")
               print (os.linesep)

          if param is None:   
               print (chr(9) + "/help: command line usage")
               print (os.linesep)

          if param is None or param == "/recentlyadded:":
               print (chr(9) + "/recentlyadded: List all files added since specified date and save results as CSV or HTML")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /recentlyadded addedsincedate filename format")
               print (chr(9) + chr(9) + "Save locally: " + sys.argv[0] + " /recentlyadded 02/28/2018 recentlyadded.csv CSV")
               print (chr(9) + chr(9) + "Save DropBox: " + sys.argv[0] + " /recentlyadded 02/28/2015 Dropbox CSV")
               print (os.linesep)

               if param is not None:
                    return
			   
          if param is None or param == "/renameplaylist":
               print (chr(9) + "/renameplaylist: Rename a playlist.")
               print (chr(9) + chr(9) + "Syntax: " + sys.argv[0] + " /renameplaylist playlistname newplaylistname")
               print (chr(9) + chr(9) + "Ex: " + sys.argv[0] + " /renameplaylist Rock Rock2 ")           
               print (os.linesep)

               if param is not None:
                    return

          sys.exit()

     # Create M3U file for the specified playlist based on the file directory structure
     def createM3U(self,playlistName,dir="."):
          try:
               playlist = ''
               mp3s = []
               mp3Found = False

               if playlist == '':
                    playlist = playlistName + '.m3u'

               os.chdir(dir)

               # This will fix relative paths by converting them to absolute paths. Fixes issue with m3u not being created when specifying relative path as download dir
               dir = os.getcwd() + self.delimiter

               for root, dirnames, filenames in os.walk(dir,followlinks=True):
                    for file in filenames:
                         root.replace(dir + self.delimiter,"") + self.delimiter + file
                         if file.endswith('.mp3'):
                              mp3Found = True
                              
                              with open(root + "/" + playlist, 'w') as out:
                                   out.write("#EXTINF: " + str(int(MP3(root + self.delimiter + file).info.length)) + "," + EasyID3(root + self.delimiter + file)['artist'][0] + " - " + EasyID3(root + self.delimiter + file)['title'][0] + os.linesep)
                                   out.write("#EXTM3U" + os.linesep)
                              
          except Exception as e:
               print("Error: " + str(e))

          if mp3Found == False:
               print("No mp3 files found in '%s'." % dir)
               
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
               fileName, filter = QFileDialog.getOpenFileName(self, 'Choose the CSV to create the playlist from', selectedFilter='*.csv')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False

               if fileName[-4:].upper() != ".CSV":
                    self.messageBox("Create Playlist From Export", "The file to create the playlist from must be a CSV file")
                    return

          # Create the new playlist and store the new playlist id
          newPlaylistId = self.mc.create_playlist(newPlaylistName)
		  
          csv.register_dialect('myDialect',delimiter = ',',quoting=csv.QUOTE_ALL,lineterminator = os.linesep)
    
          with open(fileName) as f:
               csvReader = csv.reader(f, dialect='myDialect')
               for row in csvReader:
                    self.mc.add_songs_to_playlist(newPlaylistId,row[0])

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
                    folder_metadata = self.dropBoxClient.files_get_metadata("/" + playlistName, include_deleted=False)
                    
                    # Check to see whether the folder playlistName-old exists. If it does, delete it
                    try:
                         folder_metadata = self.dropBoxClient.files_get_metadata("/" + playlistName + "-old", include_deleted=False)

                         # Delete the playlistName-old folder
                         try:
                              self.dropBoxClient.files_delete("/" + playlistName + "-old")
                         except dropbox.files.DeleteError as e:
                              print("An error occurred deleting the folder /" + playlistName + "-old with the error %s" % e)
                              sys.exit()
                    except Exception as e:
                         pass # If the folder doesn't exist, it will throw an exception so ignore this exception

                    # Rename the folder playlistName to playlistName-old
                    try:
                         self.dropBoxClient.files_move("/" + playlistName, "/" + playlistName + "-old")
                    except Exception as e:
                         print("An error occurred renaming the folder /" + playlistName + " to /" + playlistName + "-old with the error %s" % e)
                         sys.exit()
               except Exception as e:
                    pass # We need to catch this Exception when the folder playlistName doesn't exist which may be OK (it doesn't have to exist already)
            
               # Create the playlist folder
               try:
                    # CONTINUE HERE THIS DOESNT EXIST
                    self.dropBoxClient.files_create_folder("/" + playlistName)
               except Exception as e:
                    print("An error occurred creating the folder /" + playlistName + " with the error %s" % e)
                    return
          elif saveLocation == "Cancel":
               return

          # Look for the specified playlist
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in playlist["tracks"]:
                         # If the track ID was not found in the library 
                         if self.library.get(track['trackId'],"") == "":
                              continue

                         # Make API call to get the suggested file and audio byte string
                         filename, audio = self.mm.download_song(self.library[track['trackId']][0])

                         if saveLocation == "Locally":
                              # If path wasn't given at the command line prompt for it
                              if downloadPath is None:
                                   downloadPath = QFileDialog.getExistingDirectory(parent=self, dir="/", caption='Please select a directory')

                                   if downloadPath == "" or downloadPath is None:
                                       return

                              # Determine the delimiter based on the O.S.
                              if sys.platform == "win32":
                                   downloadPath = downloadPath.replace("/", "\\")
                              
                              with open(downloadPath + filename, 'wb') as f:
                                   f.write(audio)
                                   f.close()

                                   if noSubDirectories == False:
                                        artistFolder=downloadPath + self.sanitizeString(self.library[track['trackId']][3])
                                   else:
                                        artistFolder=downloadPath

                                   # Make the Artist folder if it doesn't exist
                                   if os.path.isdir(artistFolder) == False:
                                        os.mkdir(artistFolder)
                                   
                                   if noSubDirectories == False:
                                        albumFolder=artistFolder + self.delimiter + self.sanitizeString(self.library[track['trackId']][2])
                                   else:
                                        albumFolder=artistFolder

                                   # Make the Album folder if it doesn't exist
                                   if os.path.isdir(albumFolder) == False:
                                        os.mkdir(albumFolder)

                                   # Move the song to the appropriate subdirectory
                                   trackFile=albumFolder + self.delimiter + self.sanitizeString(filename,True)

                                   # os.rename will fail if the file exists already so verify if the file exists and delete it if it does
                                   if noSubDirectories == False and os.path.isfile(trackFile) == True:
                                        os.remove(trackFile)

                                   if noSubDirectories == False:
                                        os.rename(downloadPath + self.delimiter + filename,trackFile)
                         elif saveLocation == "Dropbox":
                              # Create the folder named after the artist if it doesn't exist already
                              if noSubDirectories == False:
                                   artistFolder="/" + playlistName + "/" + self.sanitizeString(self.library[track['trackId']][3])
                              else:
                                   artistFolder="/" + playlistName
                                   
                              try:
                                   # Create the folder uncoditionally because if it existed before and was deleted, we need to recreate it
                                   self.dropBoxClient.files_create_folder(artistFolder)
                              except Exception as e:
                                   pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already

                              # Create the folder named after the album if it doesn't exist already
                              if noSubDirectories == False:
                                   albumFolder=artistFolder + "/" + self.sanitizeString(self.library[track['trackId']][2])
                              else:
                                   albumFolder=artistFolder
                                   
                              try:                                   
                                   folder_metadata = self.dropBoxClient.metadata(albumFolder, include_deleted=False)

                                   #if "is_deleted" in folder_metadata and folder_metadata["is_deleted"] == False or "is_deleted" not in folder_metadata:
                                   #     self.dropBoxClient.file_create_folder(albumFolder)
                              except Exception as e:
                                   pass # Suppress warning because there seems to be an issue where this script tries to create the folder name even when it exists already

                              # We have to write the file locally first before we can upload it to Dropbox
                              with open(filename, 'wb') as input:
                                   input.write(audio)
                                   input.close()

                              # Write the file to Dropbox
                              with open(filename, 'rb') as output:
                                   trackFile=albumFolder + "/" + self.sanitizeString(filename,True)

                                   response = self.dropBoxClient.files_upload(output.read(),trackFile)

                                   output.close()

                                   os.remove(filename)

          # The m3u is only created when we are saving the songs in a playlist locally and the user hasn't specified to not create this file
          if saveLocation == "Locally" and noM3U == False:
               self.createM3U(playlistName,downloadPath)
               
          # When the user is not using command line arguments display message indicating that the download has finished using MessageBox. Otherwise print to console
          if len(sys.argv) == 1:
               self.messageBox("Download a playlist", "The download of the playlist " + playlistName + " has finished")
          else:
               sys.exit()

          return

     # Open GitHub page when update button is clicked
     def downloadUpdate(self):
          webbrowser.open(self.siteURL)

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
                    for track in playlist["tracks"]:
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
               print("Export a playlist: Invalid exportFormat type " + exportFormat)
               return

          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if exportPath is None and saveToDropbox == True:
               saveLocation = "Dropbox"
          elif exportPath is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

          if saveLocation == "Cancel":
               return

          # If path wasn't given at the command line prompt for it
          if exportPath is None and saveToDropbox == False and saveLocation == "Locally":
               exportPath = None

               exportPath = QFileDialog.getExistingDirectory(parent=self, dir="/", caption='Please select a directory')

               if exportPath == "" or exportPath is None:
                    return
          elif exportPath is None and (saveToDropbox == True or saveLocation == "Dropbox"):
               # When we are saving to Dropbox, create a temporary directory locally to save the playlists to before uploading them to Dropbox
               exportPath = tempfile.mkdtemp()
          else:
               os.chdir(exportPath)

          if sys.platform == "win32":
               exportPath = exportPath.replace("/", "\\")

          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               # Replace any characters that are not allowed in Windows filenames with _.
               playlistname = playlist["name"].replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace(":", "_").replace(chr(34), "_").replace("<", "_").replace(">", "_").replace("|", "_")

               fileName = exportPath + self.delimiter + playlistname + "." + exportFormat.lower()

               # Change to working dir. Upload to DB will fail if we don't do this but its also needed when working locally
               os.chdir(exportPath)
					
               self.exportPlaylist(playlist,playlistname + "." + exportFormat.lower(),exportFormat,saveToDropbox,True)

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
          # Make sure DB Oauth is only done once
          dropBoxOAuthCompleted = False
		  
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print("Export library: Invalid exportFormat type " + exportFormat)
               return
          
          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if fileName is None and saveToDropbox == True:
               saveLocation = "Dropbox"

               if dropBoxOAuthCompleted == False:
                    # Log into Dropbox using OAuth so we can read and write to it
                    if self.performDropboxOAuth() == False:
                         return
                
                    dropBoxOAuthCompleted  = True
          elif fileName is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

               # Log into Dropbox using OAuth so we can read and write to it if the save location chosen is Dropbox
               if saveLocation == "Dropbox" and dropBoxOAuthCompleted == False:
                    if self.performDropboxOAuth() == False:
                         return
                 
                    dropBoxOAuthCompleted  = True
          if saveLocation == "Cancel":
               return

          # If no filename was provided at the command line, prompt for one
          if fileName is None and saveToDropbox == False and saveLocation == "Locally":
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if exportFormat == "CSV":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the export', "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower(), "CSV (*.csv)")
               elif exportFormat == "HTML":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the export', "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower(), 'HTML (*.html)')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False
          elif fileName is None and (saveToDropbox == True or saveLocation == "Dropbox"):
               fileName = "My GMusic Library as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower()

          # Reference to entire catalog
          library = self.mc.get_all_songs()

          # create array from the data so we can pass the data to writeData()
          libTracks = list()

          for currTrack in library:
               row=[currTrack["id"],currTrack["title"],currTrack["album"],currTrack["artist"],currTrack["trackNumber"],currTrack["year"],currTrack["albumArtist"],currTrack["discNumber"],currTrack["genre"]]
               libTracks.append(row)

          # Write playlist
          self.writeData(fileName,exportFormat,libTracks)

          # if this function is called from the command line, this flag will be true
          if saveToDropbox == False and saveLocation == "Locally":
               if len(sys.argv) == 1:
                    self.messageBox("Export Library", "Export complete")
               else:
                    sys.exit()
          elif saveToDropbox == True or saveLocation == "Dropbox":
               if dropBoxOAuthCompleted == False:
                    # Write the file to Dropbox
                    if self.performDropboxOAuth() == False:
                         return
						 
                    dropBoxOAuthCompleted  = True

               dest_path = os.path.join('/', fileName)
               
               with open(fileName,'rb') as f:
                    self.dropBoxClient.files_upload(f.read(),dest_path)

               if len(sys.argv) == 1:
                    self.messageBox("Export Library", "Export complete")
               else:
                    sys.exit()

     # Event when the user clicks on a playlist to export
     def exportPlaylist(self, playlistName, fileName=None, exportFormat=None, saveToDropbox=False,skipDropboxOAuth=False):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print("Export a playlist: Invalid exportFormat type " + exportFormat)
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
          elif saveToDropbox == False:
               saveLocation = self.promptForSaveLocation()
		  
               if saveLocation == "Dropbox":
                    fileName = playlistName + "." + exportFormat.lower()
                    saveToDropbox = True
          else:
               saveLocation=""

          if saveLocation == "Cancel":
               return

          # If a command line argument wasn't given prompt for the location to save the playlist
          if fileName is None and saveToDropbox == False and saveLocation == "Locally":
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if exportFormat == "CSV":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the CSV playlist', playlistName + "." + exportFormat.lower(), 'CSV (*.csv)')
               elif exportFormat == "HTML":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the HTML playlist', playlistName + "." + exportFormat.lower(), 'HTML (*.html)')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return

          # exportFile = open(fileName, "w")

          playlisttracks = []

          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    # for track in sorted(playlist["tracks"]):
                    for track in playlist["tracks"]:
                         playlisttracks.append(self.library[track['trackId']])

          # Sort the playlist tracks by index 0 (The track name)
          playlisttracks = sorted(playlisttracks, key=lambda playlisttrack: playlisttrack[0])

          for playlisttrack in playlisttracks:
               playlisttrack[9:10]=[] #  Remove Timestamp and size
               playlisttrack[9:10]=[]

          # Write data
          self.writeData(fileName,exportFormat,playlisttracks)

          if saveToDropbox == False or saveLocation == "Locally":
               # If this wasn't called from the command line argument, display a message that it has completed
               if isCommandLine == False:
                    self.messageBox("Export Playlist", "The export of the playlist " + playlistName + " has completed")
               else:
                    return
          elif saveToDropbox == True or saveLocation == "Dropbox":
               if skipDropboxOAuth == False:
                    # Log into Dropbox using OAuth so we can read and write to it
                    if self.performDropboxOAuth() == False:
                         return

               dest_path = os.path.join('/', fileName)
               
               with open(fileName,'rb') as f:
                    self.dropBoxClient.files_upload(f.read(),dest_path)
			   
          if len(sys.argv) == 1:
               self.messageBox("Export Playlist", "The export of the playlist " + playlistName + " has completed")

     # Export all purchased songs to a file
     def exportPurchasedSongs(self, fileName=None, exportFormat=None, saveToDropbox=False):
          # Make sure DB Oauth is only done once
          dropBoxOAuthCompleted = False

          # Log into Google using OAuth so we can use the Musicmanager interface
          if self.performGoogleOAuth() == False:
               return

          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat = "CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               if len(sys.argv) == 1:
                    self.messageBox("Export Library", "Export complete")
               else:
                    print("Export purchased songs: Invalid exportFormat type " + exportFormat)

               return

          if exportFormat is None:
               exportFormat=self.promptForSaveFormat()

               if exportFormat=="Cancel":
                    return

          # If saveToDropbox is False, prompt for the save location. Otherwise we force a return val of Dropbox
          if fileName is None and saveToDropbox == True:
               saveLocation = "Dropbox"

               if dropBoxOAuthCompleted == False:
                    # Log into Dropbox using OAuth so we can read and write to it
                    if self.performDropboxOAuth() == False:
                         return
                
                    dropBoxOAuthCompleted  = True
          elif fileName is not None and saveToDropbox == False:
               saveLocation = "Locally"
          else:
               saveLocation = self.promptForSaveLocation()

               # Log into Dropbox using OAuth so we can read and write to it if the save location chosen is Dropbox
               if saveLocation == "Dropbox" and dropBoxOAuthCompleted == False:
                    if self.performDropboxOAuth() == False:
                         return
                 
                    dropBoxOAuthCompleted  = True
          if saveLocation == "Cancel":
               return

          if fileName is None:
               fileName = "My GMusic Purchased Songs as of " + time.strftime("%x").replace("/", "-") + "." + exportFormat.lower()
 
          # Download all purchased songs
          purchasedSongs = self.mm.get_purchased_songs()

          # Write data
          self.writeData(fileName,exportFormat,purchasedSongs)

           # if this function is called from the command line, this flag will be true
          if saveLocation == "locally" and saveToDropbox == False:
               if len(sys.argv) == 1:
                    self.messageBox("Export Purchased Songs", "Export complete")
               else:
                    sys.exit()
          elif saveLocation == "Dropbox" or saveToDropbox == True:
               # Write the file to Dropbox
               if self.performDropboxOAuth() == False:
                    return
						 
               dest_path = os.path.join('/', fileName)
               
               with open(fileName,'rb') as f:
                    self.dropBoxClient.files_upload(f.read(),dest_path)

               if len(sys.argv) == 1:
                    self.messageBox("Export Purchased Songs", "Export complete")
               else:
                    sys.exit()

     # Export the songs currently being displayed in the recently added window
     def exportRecentlyAdded(self,fileName,exportFormat,saveToDropbox):
          if exportFormat is None:
               exportFormat=self.promptForSaveFormat()
          
          if exportFormat=="Cancel":
               return

          saveLocation = ""

          if fileName is None:
               saveLocation = self.promptForSaveLocation()
          
          if saveLocation=="Locally":
               if exportFormat=="CSV":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the recently added file', "", 'CSV (*.csv)')
               else:
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the recently added file', "", 'HTML (*.html)')
               
               # If the user clicked on cancel then do nothing	
               if fileName is None or fileName == "":
                    return
          elif saveLocation == "Dropbox":
               fileName = playlistName + "." + exportFormat.lower()
          elif saveLocation == "Cancel":
               return

          self.writeData(fileName,exportFormat,self.newSongs,extendedHeader=True)
 
          if saveToDropbox == False and len(sys.argv) == 1:
               self.messageBox("Export Playlist", "The export of the recently added files has completed")
          elif saveToDropbox == True or saveLocation == "Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

             
               # Write the file to Dropbox
               dest_path = os.path.join('/', fileName)
               
               with open(fileName,'rb') as f:
                    self.dropBoxClient.files_upload(f.read(),dest_path)

     # Find duplicate tracks across 2 playlists
     def findDuplicateTracksInPlaylist(self,playlist1,playlist2,isCommandLine=False, saveToDropbox=False, fileName=None):
          playlist1IDs=set()
          playlist2IDs=set()
          
          # Loop through all tracks in playlist1 and add the ID to playlist1IDs set
          for playlist in self.playlists:
               if playlist["name"] == playlist1:
                    for track in playlist["tracks"]:
                         playlist1IDs.add(track['trackId'])

          # Loop through all tracks in playlist2 and add the ID to playlist2IDs set
          for playlist in self.playlists:
               if playlist["name"] == playlist2:
                    for track in playlist["tracks"]:
                         playlist2IDs.add(track['trackId'])                         
          
          # Compare the 2 sets and store the results in a new set
          dupeID=playlist1IDs.intersection(playlist2IDs)
          
          # When the resulting set is empty there are no duplicates
          if len(dupeID) == 0:
               # This function was not run from the command line so display message with MessageBox
               if fileName is None:
                    self.messageBox("Find duplicate tracks in playlists","There were no duplicates found between " + playlist1 + " and " + playlist2)
               else:
                    print("There were no duplicates found between " + playlist1 + " and " + playlist2)
               
               return
          
          # Transform data into array so we can write data to it
          dupes = list()

          for currID in dupeID:
               row=[self.library[currID][0],self.library[currID][1],self.library[currID][2],self.library[currID][3],self.library[currID][4],self.library[currID][5],self.library[currID][6],self.library[currID][7],self.library[currID][8]];
               dupes.append(row)

          # If filename wasn't provided, this function was run from the GUI and not the command line
          if isCommandLine == False:               
               # Get the location to save the resulting file (Locally or Dropbox)
               saveLocation = self.promptForSaveLocation()
               
               if saveLocation == "Cancel":
                    return
               
               # Prompt for the file name if the file is being saved locally
               if saveLocation == "Locally":
                    fileName, filter = QFileDialog.getSaveFileName(self, 'Choose the location to save the results of the comparison',playlist1 + " to " + playlist2 + " Comparison.csv", 'CSV (*.csv)')
               
                    # If the user clicked on cancel then do nothing
                    if fileName is None or fileName == "":
                         return False
               else:
                    fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
          elif saveToDropbox == True and fileName is None:
               saveLocation="Dropbox"
               fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
          elif saveToDropbox == False and fileName is None:
               saveLocation="Locally"
               fileName=playlist1 + " to " + playlist2 + " Comparison.csv"
          else:
               saveLocation=""

          self.writeData(fileName,"CSV",dupes)

          # Save to Dropbox if that was selected as the save location
          if saveToDropbox == True or saveLocation=="Dropbox":
               # Log into Dropbox using OAuth so we can read and write to it
               if self.performDropboxOAuth() == False:
                    return

               # Write the file to Dropbox
               dest_path = os.path.join('/', fileName)
               
               with open(fileName,'rb') as f:
                    self.dropBoxClient.files_upload(f.read(),dest_path)

          if isCommandLine==False:
               self.resetLayout()
          else:
               sys.exit()

     # Event when the user clicks on the Export As ComboBox for a library task
     def libraryExportFormatComboBoxChange(self):
          if str(self.libraryTaskComboBox.currentText()) == "Export your entire library" and self.libraryExportFormatComboBox.currentIndex() != 0:
               self.exportLibrary(None, self.libraryExportFormatComboBox.currentText())
               self.resetLayout()
          elif str(self.libraryTaskComboBox.currentText()) == "Export all purchased songs" and self.libraryExportFormatComboBox.currentIndex() != 0:
               self.exportPurchasedSongs(None, self.libraryExportFormatComboBox.currentText())
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
          elif optionItem == "Export all purchased songs":
               if self.libraryExportFormatComboBox.isHidden() == False and self.libraryExportFormatComboBox.currentIndex() != 0:
                    self.exportPurchasedSongs()
                    self.resetLayout()
               else:
                    self.libraryExportFormatLabel.show()
                    self.libraryExportFormatComboBox.show()
          else:
               self.libraryExportFormatLabel.hide()
               self.libraryExportFormatComboBox.hide()

     # Load the library of songs
     def loadLibrary(self):
          # Load library - Get Track ID,Song Title,Album,Artist and Track number for each song in the library
          #
          # We must have a try except here to trap an error since this API call will randomly return a 500 error from Google
          try:
               self.library = {song['id']: [song['id'], song['title'], song['album'], song['artist'], song['trackNumber'], song.get("year", ""), song['albumArtist'], song['discNumber'], song.get("genre", ""), song.get("creationTimestamp",""), song.get("estimatedSize","")] for song in self.mc.get_all_songs()}
          except:
               # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
               if len(sys.argv) == 1:
                    self.messageBox("Library Error", "An error occurred while getting the list of songs in your library. Please try again")
               else:
                    print("An error occurred while getting the list of songs in your library. Please try again")
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
          QMessageBox.question(self, title, message, QMessageBox.Ok)

          return True

     # Display MessageBox with Yes/No Buttons
     def messageBox_YesNo(self, title, message):
          reply = QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

          if reply == QMessageBox.Yes:
               return "YES"
          else:
               return "NO"

     # Parse and validate command line arguments
     def parseCommandLineArguments(self):
          validParameter = False

          # Command line arguments are the # of total parameters required including the app
          claParameters = {"/checkforupdates" : 1, "/createplaylist" : 3, "/deleteplaylist" : 2, "/downloadplaylist" : 3, "/duplicateplaylist" : 3, "/exportlibrary":3, "/exportpurchasedsongs":3, "/exportplaylist": 4, "/exportallplaylists":3, "/findduplicates":4,"/help": 1, "/recentlyadded":4, "/renameplaylist":3}

          # No command line arguments
          if len(sys.argv) == 1:
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
                         print(os.linesep + os.linesep + "Invalid number of command line parameter(s) given for " + sys.argv[1] + ". Expected " + str(claParameters[key]) + " parameters but received " + str(len(sys.argv)-1) + " parameters")
                         self.commandLineUsage(sys.argv[1])
                         sys.exit()

          # If the parameter isn't valid
          if validParameter == False:
               print("os.linesep + os.linesep + Invalid command line parameter(s) " + sys.argv[1])
               self.commandLineUsage()
               sys.exit()

          if sys.argv[1] == '/help' or sys.argv[1] ==  "/?":
               if not sys.argv[2] is None:
                    self.commandLineUsage(sys.argv[2])
               else:
                    self.commandLineUsage()
          elif sys.argv[1] == "/checkforupdates":
               self.checkForUpdate()
               sys.exit()
          elif sys.argv[1] == "/createplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2] and AllowDuplicatePlaylistNames == False:
                         print(os.linesep + os.linesep + "The new playlist name that you specified: " + sys.argv[2] + " exists already. Please use a different name or use /deleteplaylist first to delete the playlist")
                         self.commandLineUsage("/createplaylist")
                         sys.exit()
               if str(sys.argv[3])[-4:].upper() != ".CSV":
                    print(os.linesep + os.linesep + "The filename argument for /createplaylist must be a CSV file")
                    self.commandLineUsage("/createplaylist")
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
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
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
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
                    sys.exit()

               self.loadLibrary()

               if sys.argv[3].upper() == "DROPBOX":
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
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
                    self.commandLineUsage("/duplicateplaylist")
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3] and AllowDuplicatePlaylistNames == False:
                         print(os.linesep + os.linesep + "The new playlist name " + sys.argv[3] + " already exists. Please use /deleteplaylist first to delete the playlist")
                         self.commandLineUsage("/duplicateplaylist")
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/exportlibrary":
               # Convert the export format to upper case
               sys.argv[3] = sys.argv[3].upper()

               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print(os.linesep + os.linesep + "The export format " + sys.argv[3] + " is not valid.")
                    self.commandLineUsage("/exportlibrary")
                    sys.exit()

               if sys.argv[2].upper() == "DROPBOX":
                    self.exportLibrary(None, sys.argv[3], True)
               else:
                    self.exportLibrary(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/exportpurchasedsongs":
               # Convert the export format to upper case
               sys.argv[3] = sys.argv[3].upper()

               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print(os.linesep + os.linesep + "The export format " + sys.argv[3] + " is not valid.")
                    self.commandLineUsage("/exportpurchasedsongs")
                    sys.exit()

               if sys.argv[2].upper() == "DROPBOX":
                    self.exportPurchasedSongs(None, sys.argv[3], True)
               else:
                    self.exportPurchasedSongs(sys.argv[2], sys.argv[3])
          elif sys.argv[1] == "/exportplaylist":
               # Convert the export format to upper case
               sys.argv[4] = sys.argv[4].upper()
               
               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print(os.linesep + os.linesep + "The export format " + sys.argv[4] + " is not valid.")
                    self.commandLineUsage("/exportplaylist")
                    sys.exit()
               self.playlists = self.mc.get_all_user_playlist_contents()

               self.loadLibrary()

               # Validate that the playlist is a valid one
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
                    self.commandLineUsage("/exportplaylist")
                    sys.exit()

               if sys.argv[3].upper() == "DROPBOX":
                    self.exportPlaylist(sys.argv[2], None, sys.argv[4], True)
               else:
                    self.exportPlaylist(sys.argv[2], sys.argv[3], sys.argv[4])
          elif sys.argv[1] == "/exportallplaylists":
               # Convert the export format to upper case
               sys.argv[3] = sys.argv[3].upper()

               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print(os.linesep + os.linesep + "The export format " + sys.argv[3] + " is not valid.")
                    self.commandLineUsage("/exportallplaylists")
                    sys.exit()

               self.playlists = self.mc.get_all_user_playlist_contents()

               self.loadLibrary()

               if sys.argv[2].upper() == "DROPBOX":
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
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
                    self.commandLineUsage("/findduplicates")
                    sys.exit()

               # Second playlist
               validPlaylist = False
               
               self.playlists = self.mc.get_all_user_playlist_contents()

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3]:
                         validPlaylist = True

               if validPlaylist == False:
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[3] + " does not exist")
                    self.commandLineUsage("/findduplicates")
                    sys.exit()

               # We need to load the library because we have to get all of the track information
               self.loadLibrary()
               
               if sys.argv[4].upper() == "DROPBOX":
                    self.findDuplicateTracksInPlaylist(sys.argv[2], sys.argv[3],True,True)
               else:
                    self.findDuplicateTracksInPlaylist(sys.argv[2], sys.argv[3], True,False,sys.argv[4])
          elif sys.argv[1] == "/recentlyadded":
               # Convert the export format to upper case
               sys.argv[4] = sys.argv[4].upper()

               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print(os.linesep + os.linesep + "The export format " + sys.argv[4] + " is not valid.")
                    self.commandLineUsage("/recentlyadded")
                    sys.exit()

               try:
                    # This will raise ValueError if sys.argv[2] is not a valid date
                    asofDate = datetime.datetime.strptime(sys.argv[2], '%m/%d/%Y')
                    asofDate = asofDate.date()

                    # Load library
                    self.loadLibrary()

                    # Call buildRecentlyAddedWindow() to save the file
                    if sys.argv[3].upper() == "DROPBOX":
                          self.buildRecentlyAddedWindow(asofDate, None, sys.argv[4], True)
                    else:
                         self.buildRecentlyAddedWindow(asofDate, sys.argv[3], sys.argv[4])
               except ValueError:
                    print(os.linesep + os.linesep + "The recently added date " + sys.argv[2] + " is not valid")
                    self.commandLineUsage("/recentlyadded")
                    sys.exit()
          elif sys.argv[1] == "/renameplaylist":
               self.playlists = self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[2]:
                         validPlaylist = True

               if validPlaylist == False:
                    print(os.linesep + os.linesep + "The playlist " + sys.argv[2] + " does not exist")
                    self.commandLineUsage("/renameplaylist")
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist = False

               for playlist in self.playlists:
                    if playlist["name"] == sys.argv[3] and AllowDuplicatePlaylistNames == False:
                         print(os.linesep + os.linesep + "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist")
                         self.commandLineUsage("/renameplaylist")
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2], sys.argv[3], True)

          sys.exit()

     # Perform Dropbox authentication so we can read and write to it
     def performDropboxOAuth(self):
          dropBoxFilename = "DropboxOauth.cred"
          
          dbx = dropbox.Dropbox(base64.b64decode("bFJ6Sjl5ZHI3TWtBQUFBQUFBQjNaWjE0MTFsbk1JeDYyMVdnaUpDcFBGUWZ3Vk5xSWhDdEtBRFhoVFJhbm1jclZwTmJockRoZ1dSanBMenlhWklTaG1QcXU=").replace(self.salt,""))
          
          # If the Dropbox oauth access code file doesn't exist, initiate the Oauth process through Dropbox
          if os.path.isfile(dropBoxFilename) == False:
               flow = DropboxOAuth2FlowNoRedirect(base64.b64decode("NXVubTRvMm9idnRpNjhvVnBOYmhyRGhnV1JqcEx6eWFaSVNobVBxdQ==").replace(self.salt,""),base64.b64decode("Mm9ncGllaXg2ZG9vOG51VnBOYmhyRGhnV1JqcEx6eWFaSVNobVBxdQ==").replace(self.salt,""))
               print("Step 2: " + base64.b64decode("NXVubTRvMm9idnRpNjhvVnBOYmhyRGhnV1JqcEx6eWFaSVNobVBxdQ==").replace(self.salt,""))
               print("Step 3: " + base64.b64decode("Mm9ncGllaXg2ZG9vOG51VnBOYmhyRGhnV1JqcEx6eWFaSVNobVBxdQ==").replace(self.salt,""))
               authorize_url = flow.start()

               # Allow OAuth prompt to be displayed in console
               if len(sys.argv) == 1:
                    self.messageBox("Dropbox OAuth", "When you click on OK, this script will open a web browser window asking you to allow GMusicUtility to connect to your Dropbox account (you might have to log in first). Please click on Allow and copy the authorization code into the command prompt window")
                    webbrowser.open(authorize_url)
               else:
                    print("Please log into DropbBox in your browser and then visit the URL " + authorize_url + ". After allowing Google Play Music Utility, paste the code here.")

               if sys.version_info[0] == 2:
                    code = raw_input("Enter the authorization code here: ")
               else:
                    code = input("Enter the authorization code here: ")

               # This will fail if the user enters an invalid authorization code
               try:
                    access_token = flow.finish(code)
               except dbrest.ErrorResponse as e:
                    print('DropBox Error: %s' % e)
                    return False

               self.dropBoxClient = dropbox.Dropbox(access_token.access_token)

               dbaccess = open(dropBoxFilename, "w")
               dbaccess.write(access_token.access_token)
               dbaccess.close()
          else:
               dbaccess = open(dropBoxFilename, "r")
               access_token = dbaccess.readline()
               dbaccess.close()

               try:
                    self.dropBoxClient = dropbox.Dropbox(access_token)
               except:
                    if len(sys.argv) == 1:
                         self.messageBox("Dropbox authentication failed", "Your Dropbox authentication has failed. Please make sure that you entered a valid code.")
                    else:
                         print("Your Dropbox authentication has failed. Please make sure that you entered a valid code.")

                    return False

     # Perform Google OAuth authentication because we need to use OAuth when using the Musicmanager interface
     def performGoogleOAuth(self):		  
          if os.path.isfile(self.GoogleMMOAuthCredFile) == False:
               try:
                    print("Trying to auth because no existing file")
                    self.mm.perform_oauth(self.GoogleMMOAuthCredFile, True)
               except:
                    print("Exception occurred")
                    if len(sys.argv) == 1:
                         self.messageBox("Google Play Music authentication failed", "Your Google Play Music authentication has failed. Please make sure that you entered a valid code.")
                         return False                         
                    else:
                         print("Your Google Play Music authentication has failed. Please make sure that you entered a valid code.")
                         return False
                         
               return True
          else:
               try:
                    # Login using GoogleOAuth.cred
                    self.mm.login(self.GoogleMMOAuthCredFile)
               except AlreadyLoggedIn:
                     return True
               except ValueError:
                    print("Value Error")
               except OSError:
                    print("OS Error")
               except Exception as e:
                    print(e);
                    return False

          return True

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
          custDialog = QMessageBox()
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
          custDialog = QMessageBox()
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
  
     # String cleanser
     def sanitizeString(self,str,isFile=False):
          origStr=str

          # get index of period in filename based on index from the end of the file
          if str.find(".") != -1:
               extIndex=(len(str) - str.find("."))*-1
          else:
               extIndex=-1

          str=slugify(str)
           
          if isFile == True:
               str=str.replace("-"," - ")
               
               if extIndex != -1 and origStr[extIndex] == ".":
                    str=str.replace(str[(extIndex+1):],"." + str[(extIndex+1):])
          else:
              str = str.replace("-"," ")

          str=str.title()

          if isFile == True:
               str=str.replace(str[(extIndex+1):],str[(extIndex+1):].lower())

          badChars = ['/','\\',':','*','?','"','<','>','|']
          
          for currChar in badChars:
               str.replace(currChar,'_')

          return str

     # Show user dialog and return the result
     def showDialog(self, title, promptText):
          # the result of user input. It is "" when user clicks on ok without entering anything or None when they cancel the dialog
          result = None

          text, ok = QInputDialog.getText(self, title, promptText)

          if ok:
               return str(text)
          else:
               return None

     # Write data to file
     def writeData(self,fileName,exportFormat,data,extendedHeader=False):
          if exportFormat =="CSV":
               with open(fileName, 'w') as f:
                    csv.register_dialect('myDialect',delimiter = ',',quoting=csv.QUOTE_ALL,lineterminator = '\n')

                    writer = csv.writer(f, dialect='myDialect')

                    if extendedHeader == False:
                         writer.writerow(self.csvHeader)
                    else:
                         newCSVHeader=self.csvHeader
                         newCSVHeader.append("Date Added")
                         newCSVHeader.append("File Size")
                         writer.writerow(newCSVHeader)

                    for track in data:
                         writer.writerow(track)
          elif exportFormat == "HTML":
               with open(fileName, 'w') as out:
                    # Recently added has an extended header with 2 extra columns
                    if extendedHeader == False:
                         out.write(self.HTMLHeader)
                    else:
                         out.write(self.HTMLHeader.replace("</TR>" + os.linesep,"<TD>Date Added</TD><TD>File Size</TD></TR>" + os.linesep))
                    
                    for track in data:
                         row="<TR>"
                         for num in range(0, len(track)):
                              row+="<TD>" + str(track[num]) + "</TD>"

                         row+="</TR>" + os.linesep	 
                         
                         out.write(row)

                    out.write(self.HTMLFooter)

          return fileName

app = QApplication(sys.argv)


# If the user specifies /help as a command line argument, display the usage without worrying if the login credentials are stored
if len(sys.argv) == 2 and (sys.argv[1] == "/help" or sys.argv[1] == "/?"):
     gMusicUtility = GMusicUtility()
     sys.exit()

     # When login credentials aren't stored or set to defaults and command line arguments are being used, do not display login
     if len(sys.argv) > 1:
          print("Error: The login information is not stored. Please edit this script with your login information if you want to use command line arguments")
          sys.exit()

else:
     gMusicUtility = GMusicUtility()

sys.exit(app.exec_())
