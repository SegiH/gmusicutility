import ctypes
import datetime
from datetime import date, timedelta
import operator
import re
import sys
import time
import tkFileDialog
import tkMessageBox
import urllib2
import webbrowser
from gmusicapi.clients import Mobileclient
from PySide import QtGui
from PySide import QtCore
from PySide.QtCore import *
from PySide.QtGui import *

# To Do
#
# reorder playlist

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
username="mygmailaddress@gmail.com"
password="mypassword"

tableForegroundColor=None

tableBackgroundColor=None
	
# Change this to True if you want to allow duplicate playlist names (not recommended because it can cause problems)
AllowDuplicatePlaylistNames=False

### DO NOT EDIT ANYTHING BELOW THIS LINE
class Login(QtGui.QDialog):
     def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setWindowTitle('Google Play Music Login')
        self.resize(500,60)
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
        if (self.textName.text() != '' and self.textPass.text() != ''):
            self.accept()
            
        else:
            QtGui.QMessageBox.warning(
                self, 'Error', 'Please enter the username and password')
     
     def getCreds(self):
          return [self.textName.text(),self.textPass.text()]

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
        self.mylist = sorted(self.mylist,
            key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.emit(SIGNAL("layoutChanged()"))
     
    def dragMoveEvent(self, event):
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()

    def moveRows(self, parent, source_first, source_last, parent2, dest):
        print "moveRows called, self.data = %s" % self.data
        self.beginMoveRows(parent, source_first, source_last, parent2, dest)

        self.data = self.data[1] + self.data[0] + self.data[2]
        self.endMoveRows()
        print "moveRows finished, self.data = %s" % self.data

class TableView(QTableView):
    def __init__(self, parent=None):
        QTableView.__init__(self, parent=None)
        self.setSelectionMode(self.ExtendedSelection)
        self.setDragEnabled(True)
        self.acceptDrops()
        self.setDragDropMode(self.InternalMove)
        self.setDropIndicatorShown(True)
    '''
    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        print "dropEvent called"
        point = event.pos()
        self.model().moveRows(QModelIndex(), 0, 0, QModelIndex(), 1)
        event.accept()

    def mousePressEvent(self, event):
        print "mousePressEvent called"
        self.startDrag(event)

    def startDrag(self, event):
        print "startDrag called"
        index = self.indexAt(event.pos())
        if not index.isValid():
            return

        self.moved_data = self.model().data[index.row()]

        drag = QDrag(self)

        mimeData = QMimeData()
        mimeData.setData("application/blabla", "")
        drag.setMimeData(mimeData)

        pixmap = QPixmap()
        pixmap = pixmap.grabWidget(self, self.visualRect(index))
        drag.setPixmap(pixmap)

        result = drag.start(Qt.MoveAction)
     '''   
     
class GMusicUtility(QtGui.QWidget):
     mc=None
     
     global tableForegroundColor
     global tableBackgroundColor
     
     # playlist header used on all exports
     csvHeader="Track ID,Track Name,Album,Artist,Track Number,Year,Album Artist,Disc Number,Genre\n"

     # HTML header used on all exports
     HTMLHeader=None
         
     # HTML Footer used on all exports
     HTMLFooter="</TABLE>\n</BODY>\n</HEAD>\n</HTML>"

     playlists=None

     library=None
     
	 # App Version - Used to check for updates
     version="2.1"
	 
     # Export As ComboBox
     libraryExportFormatComboBox=None

     # Export As label
     playlistExportFormatLabel=None

     # Export As Option Menu
     playlistExportFormatComboBox=None

     # Library Task label
     libraryTaskLabel=None

     # Library tasks ComboBox
     libraryTaskComboBox=None

     # Playlist label - needs to be dynamically show and hidden as needed
     playlistLabel=None

     # Playlist ComboBox - needs to be dynamically show and hidden as needed
     playlistComboBox=None

     # Playlist Task ComboBox
     playlistTaskComboBox=None

     # Rename Playlist Table
     renameTable=None
     
     # Rename Playlist Widget
     renameWidget=None
     
	# Recently Added Widget
     recentlyAddedWidget=None
     
     recentlyAddedLabel=None
     
     recentlyAddedDateEdit=None
    
     table_view=None
     
     recentlyAddedLayout=None
     
     recentlyAddedYear=0
     
     recentlyAddedMonth=0
     
     recentlyAddedDay=0
     
     # Window width & height
     width=580     
     height=150

     # Coordinates for the controls for each column (X coordinate)
     columnXCoordinates=[15,225,480]

     # Coordinates for the controls for each row (Y coordinate)     
     rowYCoordinates=[20,40,80,100]

     validFormats = ["CSV","HTML"]
     
     def __init__(self,username,password):
          super(GMusicUtility, self).__init__()
          
		  # Before logging in, check my site to see if  there is an update for this script
          data = urllib2.urlopen("http://www.hovav.org/GMusicUtility/latestversion.txt")
          
		  # Read the text file which contains only 1 line which is the latest version number
          for line in data:
               if (line != self.version):
                    result=self.messageBox_YesNo("Google Play Music Utility Updater","There is an updated version of this script available. Would you like to download it now ?")
					
                    if result=="YES":
                         webbrowser.open('http://apps.hovav.org/google-play-music-utility/')

          self.mc = Mobileclient()

          if self.mc.login(username,password) == False:
               # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
               if len(sys.argv) == 1:
                    self.messageBox("Google Play Music Utility","Unable to log into your Google account. Please check your login credentials")
                    sys.exit()
               else:
                    print "Unable to log into your Google account. Please check your login credentials"
                    sys.exit()
          
          if tableForegroundColor is None or tableBackgroundColor is None:
               # Default
               self.HTMLHeader="<HTML>\n<HEAD>\n<STYLE>\ntable td {\n     border-style: solid;\n    border-width: 0px;\n    border-color:red;\n    background-color:#303030;\n    color:white;\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1>\n<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD></TR>\n"
          elif tableForegroundColor is not None and tableBackgroundColor is not None:
               # Validate the provided foreground and background colors.
          
               _rgbstring = re.compile(r'#[a-fA-F0-9]{6}$')
          
               # Validate that tableForegroundColor is a valid hex number
               if (bool(_rgbstring.match(tableForegroundColor))==False):
                    self.messageBox("Recently Added","tableForegroundColor is not a valid hex number. Please use only 0-9 and A-F with a leading #")
                    sys.exit()

               # Validate that tableBackgroundColor is a valid hex number
               if (bool(_rgbstring.match(tableBackgroundColor))==False):
                    self.messageBox("Recently Added","tableBackgroundColor is not a valid hex number. Please use only 0-9 and A-F with a leading #")
                    sys.exit()
          
               self.HTMLHeader="<HTML>\n<HEAD>\n<STYLE>\ntable td {\n     border-style: solid;\n    border-width: 0px;\n    border-color:red;\n    background-color:" + str(tableBackgroundColor) + ";\n    color:" + str(tableBackgroundColor) + ";\n}\n</STYLE>\n<BODY>\n<TABLE BORDER=1>\n<TR><TD>Track ID</TD><TD>Track Name</TD><TD>Album</TD><TD>Artist</TD><TD>Track Number</TD><TD>Year</TD><TD>Album Artist</TD><TD>Disc Number</TD><TD>Genre</TD></TR>\n"
          # parse command line arguments before loading any data from the web.
          self.parseCommandLineArguments()

          self.buildMainWindow()
		  
     # Build the main screen
     def buildMainWindow(self):
          self.resize(self.width,self.height)
          self.setWindowTitle('Google Play Music Utility ' + self.version)

          leftPadding=25
		  
          ### Column 1 ###
          
          # Playlist Task Options Label
          self.playlistTaskLabel=QtGui.QLabel(self)
          self.playlistTaskLabel.setText("Playlist Options")
          self.playlistTaskLabel.move(self.columnXCoordinates[0],self.rowYCoordinates[0])

          # Playlist Task ComboBox
          self.playlistTaskComboBox = QtGui.QComboBox(self)
          self.playlistTaskComboBox.addItem(None)
          self.playlistTaskComboBox.addItem("Create a playlist from CSV")
          self.playlistTaskComboBox.addItem("Delete a playlist")
          self.playlistTaskComboBox.addItem("Duplicate a playlist")
          self.playlistTaskComboBox.addItem("Export a playlist")
          self.playlistTaskComboBox.addItem("Export all playlists")
          self.playlistTaskComboBox.addItem("Rename a playlist")
          #self.playlistTaskComboBox.addItem("Reorder a playlist")
          
          self.playlistTaskComboBox.move(self.columnXCoordinates[0],self.rowYCoordinates[1])
          self.playlistTaskComboBox.activated[str].connect(self.playlistTaskComboBoxChange)
          
          # Library Task Label
          self.libraryTaskLabel=QtGui.QLabel(self)
          self.libraryTaskLabel.setText("Library Options")
          self.libraryTaskLabel.move(self.columnXCoordinates[0],self.rowYCoordinates[2])

          # Library Task ComboBox
          self.libraryTaskComboBox = QtGui.QComboBox(self)
          self.libraryTaskComboBox.addItem(None)
          self.libraryTaskComboBox.addItem("Export your entire library")
          self.libraryTaskComboBox.addItem("View recently added files")
          self.libraryTaskComboBox.activated[str].connect(self.libraryTaskComboBoxChange)
          self.libraryTaskComboBox.move(self.columnXCoordinates[0],self.rowYCoordinates[3])

          ### Column 2 ###
          
          # Playlist Label
          self.playlistLabel=QtGui.QLabel(self)
          self.playlistLabel.setText("Playlist")
          self.playlistLabel.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[0])
          self.playlistLabel.hide()
          
          # Playlist ComboBox
          self.playlistComboBox = QtGui.QComboBox(self)
          self.playlistComboBox.move(self.columnXCoordinates[1]+(leftPadding*2),self.rowYCoordinates[0])
          self.playlistComboBox.activated[str].connect(self.playlistComboBoxChange)
          
          # Library Export Format Label
          self.libraryExportFormatLabel=QtGui.QLabel(self)
          self.libraryExportFormatLabel.setText("Export as")
           
          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.libraryExportFormatLabel.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[2])
          self.libraryExportFormatLabel.hide()
		  
          # Library Export Format ComboBox          
          self.libraryExportFormatComboBox = QtGui.QComboBox(self)
          self.libraryExportFormatComboBox.addItem(None)
          self.libraryExportFormatComboBox.addItem("CSV")
          self.libraryExportFormatComboBox.addItem("HTML")
          self.libraryExportFormatComboBox.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[3])
          self.libraryExportFormatComboBox.activated[str].connect(self.libraryExportFormatComboBoxChange)
          self.libraryExportFormatComboBox.hide()
          
          # Recently Added Label
          self.recentlyAddedLabel=QtGui.QLabel(self)
          self.recentlyAddedLabel.setText("Added since")
           
          # Move the label relative to the width() of the library dropdown since I never know exactly how wide it will be
          self.recentlyAddedLabel.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[2])
          self.recentlyAddedLabel.hide()
          
          # Recently Added ComboBox
          self.recentlyAddedDateEdit=QtGui.QDateEdit(self)
          self.recentlyAddedDateEdit.setCalendarPopup(True)
          self.recentlyAddedDateEdit.setDisplayFormat('MM/dd/yyyy')
          self.recentlyAddedDateEdit.setFixedWidth(130)
          
          # Set the default date to current date-30 days
          d = date.today() - timedelta(days=30)
          self.recentlyAddedDateEdit.setDate(d)
          
          # This must be called for the event handler to work
          self.recentlyAddedDateEdit.calendarWidget().installEventFilter(self)
          
          # Bind the event when the date changes
          self.recentlyAddedDateEdit.connect(self.recentlyAddedDateEdit.calendarWidget(),QtCore.SIGNAL('selectionChanged()'), self.recentlyAddedDateEditChange)
          
          # Event when the user types in the QDateEdit control. Keyboard presses are ignore because events are triggered as soon as the control changes
          self.recentlyAddedDateEdit.connect(self.recentlyAddedDateEdit,QtCore.SIGNAL('keyPressEvent()'),self.recentlyAddedDateEditKeypress)
          
          # Move the date dropdown to the same location as self.libraryExportFormatComboBox
          self.recentlyAddedDateEdit.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[3])
          
          # Hide it initially
          self.recentlyAddedDateEdit.hide()
          
          # Load all playlists into the playlist ComboBox
          self.loadPlaylists()

          self.playlistComboBox.hide()
          self.playlistComboBox.move(self.columnXCoordinates[1]+leftPadding,self.rowYCoordinates[1])
          self.playlistComboBox.activated[str].connect(self.playlistComboBoxChange)
          
          ### Column 3 ###
          
          # Export Format Label
          self.playlistExportFormatLabel=QtGui.QLabel(self)
          self.playlistExportFormatLabel.setText("Export as")
           
          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatLabel.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2),self.rowYCoordinates[0])
          self.playlistExportFormatLabel.hide()
          
          # Export Format ComboBox
          self.playlistExportFormatComboBox = QtGui.QComboBox(self)
          self.playlistExportFormatComboBox.addItem(None)
          self.playlistExportFormatComboBox.addItem("CSV")
          self.playlistExportFormatComboBox.addItem("HTML")
          self.playlistExportFormatComboBox.hide()
           
          # Move the label relative to the width() of the playlist dropdown since I never know exactly how wide it will be
          self.playlistExportFormatComboBox.move(self.columnXCoordinates[1]+(self.playlistComboBox.width()*2)+(leftPadding*2),self.rowYCoordinates[1])
          self.playlistExportFormatComboBox.activated[str].connect(self.playlistExportFormatComboBoxChange)
          self.show()
          
     # Create the rename a playlist window
     def buildRecentlyAddedWindow(self,asOf=None,fileName=None,exportFormat=None):          
          # Date to find songs that have been added since 30 days ago
          #asofDate=date.today() - timedelta(days=30)
          
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat="CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               if asOf is None:
                    self.messageBox("Recently Added","Invalid exportFormat type " + exportFormat)
               else:
                    print "Recently Added: Invalid exportFormat type " + exportFormat
               return
               
               return
               
          # Build date object based on function parameter asOf if given, otherwise use the value in DateTimeEdit control
          if asOf is None:
               asofDate=datetime.date(self.recentlyAddedYear,self.recentlyAddedMonth,self.recentlyAddedDay)
          else:
               asofDate=datetime.date(asOf.year,asOf.month,asOf.day)
               
          newSongs=[]
	  
          # Convert date from seconds to Microseconds (Milliseconds*1000)
          asofDateMS=time.mktime(asofDate.timetuple()) * 1000000

          asofDateMS=int(asofDateMS)
          
		# Add all songs with creationTimestamp > asofDate to an array
          for currNewSong in self.library:
               if long(self.library[currNewSong][9]) > asofDateMS:
                    # if we are exporting to CSV, get all available columns from self.library
                    if fileName is not None:
                         newSongs.append([self.library[currNewSong][0],self.library[currNewSong][1],self.library[currNewSong][2],self.library[currNewSong][3],self.library[currNewSong][4],self.library[currNewSong][5],self.library[currNewSong][6],self.library[currNewSong][7],self.library[currNewSong][8]])
                    else:
                         # Otherwise, only add Artist,Album,Track and Track Number
                         newSongs.append([self.library[currNewSong][3],self.library[currNewSong][2],self.library[currNewSong][1],self.library[currNewSong][4]])
          
          # Sort by Artist (Index 1)
          newSongs=sorted(newSongs,key=lambda newsong:newsong[0], reverse=True)

          if len(newSongs)==0:
               # If asOf is None, this function was not called from the command line
               if asOf is None:
                    self.messageBox("Recently Added","There were no songs added since the specified date")
               else:
                    print "There were no songs added since the specified date"
               return
          
          # When command line arguments were provided use them here
          if asOf is not None:
               recentlyAddedFile=open(fileName,"w")
               
               # CSV Header
               if exportFormat == "CSV":
                    recentlyAddedFile.write(self.csvHeader)
               elif exportFormat == "HTML":
                    recentlyAddedFile.write(self.HTMLHeader)
               
               for currNewSong in newSongs:
                    currTrack=self.library[currNewSong]
                    
                    if exportFormat == "CSV":
                         recentlyAddedFile.write('"' + currTrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write('"' + currTrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write(str(currTrack[4]) + ',')
                         recentlyAddedFile.write(str(currTrack[5]) + ',')
                         recentlyAddedFile.write('"' + currTrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         recentlyAddedFile.write(str(currTrack[7]) + ',')
                         recentlyAddedFile.write('"' + currTrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '"\n')
                    elif exportFormat == "HTML":
                         # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                         if (currTrack[0] == ""): currTrack[0]="&nbsp;"
                         if (currTrack[1] == ""): currTrack[1]="&nbsp;"
                         if (currTrack[2] == ""): currTrack[2]="&nbsp;"
                         if (currTrack[3] == ""): currTrack[3]="&nbsp;"
                         if (currTrack[4] == ""): currTrack[4]="&nbsp;"
                         if (currTrack[5] == ""): currTrack[5]="&nbsp;"
                         if (currTrack[6] == ""): currTrack[6]="&nbsp;"
                         if (currTrack[7] == ""): currTrack[7]="&nbsp;"
                         if (currTrack[8] == ""): currTrack[8]="&nbsp;"
                        
                         recentlyAddedFile.write("<TR>")
                         recentlyAddedFile.write("<TD>" + currTrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("<TD>" + str(currTrack[4]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + str(currTrack[5]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                              
                         recentlyAddedFile.write("<TD>" + str(currTrack[7]) + "</TD>")
                         recentlyAddedFile.write("<TD>" + currTrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         recentlyAddedFile.write("</TR>\n")
                         
               if exportFormat == "HTML":
                    recentlyAddedFile.write(self.HTMLFooter)

               recentlyAddedFile.close()
               
               sys.exit()
          
          self.recentlyAddedWidget=QtGui.QWidget()
          self.recentlyAddedWidget.showMaximized()
          self.recentlyAddedWidget.setWindowTitle("Click on column title to sort")
          
          table_model = TableModel(self,newSongs,["Artist","Album","Track","Track Number"])
		   
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

          self.recentlyAddedLayout.addWidget(self.table_view)
          self.recentlyAddedWidget.setLayout(self.recentlyAddedLayout)

          if self.recentlyAddedYear == 0:
               self.recentlyAddedWidget.show()

     # Create the rename a playlist window
     def buildReorderPlaylistWindow(self,playlistName):
          if self.renameWidget is None:
               self.renameWidget=QtGui.QWidget()
               self.renameWidget.resize(self.width,self.height)
               self.renameWidget.setWindowTitle("Click on column title to sort")
       
          songArray=[]
          tableWidgetArray=[]
          
          # Loop through all tracks in the playlist and add Track ID,Track Name,Artist and Album to an array
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         songArray.append([self.library[track['trackId']][0],self.library[track['trackId']][1] + " " + self.library[track['trackId']][3] + " " + self.library[track['trackId']][2]])

          table_model = TableModel(self,songArray,["Song ID","Name, Artist and Album"])
          
          table_view = TableView()
          table_view.setModel(table_model)
          table_view.hideColumn(0)
          table_view.resizeColumnsToContents()
          
          # set font
          font = QFont("Courier New", 14)
        
          table_view.setFont(font)
          
          # set column width to fit contents (set font first!)
          # table_view.resizeColumnsToContents()
        
          # enable sorting
          table_view.setSortingEnabled(True)
          
          ### Continue here try to enable drag and drop ####
          #table_view.setDragEnabled(True)
          #table_view.setAcceptDrops(True)
          #table_view.setDragDropOverwriteMode(True)
          #table_view.setDragDropMode(QAbstractItemView.InternalMove)
          #table_view.setSelectionMode(QtGui.QAbstractItemView.SingleSelection) 
          #table_view.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
          
          layout = QVBoxLayout(self.renameWidget)
          layout.addWidget(table_view)
          self.renameWidget.setLayout(layout)
        
          self.renameWidget.show()

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
          print "Duplicate a playlist: " + sys.argv[0] + " /duplicateplaylist playlistname newplaylistname\nEx: " + sys.argv[0] + " /duplicateplaylist Rock Rock2"
          print
          print "Export a playlist: " + sys.argv[0] + " /exportplaylist playlistname filename format\nEx: " + sys.argv[0] + " /exportplaylist Rock c:\RockPlaylist.csv CSV"
          print
          print "Export all playlists: " + sys.argv[0] + " /exportallplaylists path format\nEx: " + sys.argv[0] + " /exportallplaylists c:\playlists HTML"
          print
          print "Export library: " + sys.argv[0] + " /exportlibrary filename format\nEx: " + sys.argv[0] + " /exportlibrary c:\MyLibrary.csv CSV"
          print
          print "Recently added since: " + sys.argv[0] + " /recentlyadded addedsincedate filename format\nEx: " + sys.argv[0] + " /recentlyadded 02/28/2015 recentlyadded.csv CSV"
          print
          print "Rename a playlist: " + sys.argv[0] + " /renameplaylist playlistname newplaylistname\nEx: " + sys.argv[0] + " /renameplaylist Rock Rock2"
          print

          sys.exit()

     # Event when the user clicks on Create A Playlist From CSV
     def createPlaylistFromCSV(self,newPlaylistName=None,fileName=None):
          importFile=None
        
          # If no command line parameters were given
          if newPlaylistName is None:   
               # Display the prompt modally
               newPlaylistName=self.showDialog("Create playlist from CSV","Please enter the name of the playlist that you want to create")
        
               # When the dialog result is None, the user cancelled the dialog or clicked on OK without entering a playlist name
               if newPlaylistName == None or newPlaylistName == "":
                    return

               # Check to see if there is already a playlist with the same name as the one that will be created
               # If there is one, confirm with the user that they want to create a duplicate playlist
               playlistNames=[]
        
               # Add all playlist names to an array
               for playlist in self.playlists:
                    playlistNames.append(playlist["name"])

               # Sort the array
               playlistNames.sort()

               # Loop through all playlists. If the new playlist name chosen is in use, confirm with the user before creating a new playlist with the same name as another existing playlist
               for playlist in playlistNames:
                    if playlist==newPlaylistName and AllowDuplicatePlaylistNames==False:
                         result=self.messageBox_YesNo("Playlist name exists already","The new playlist name that you entered exists already. Are you sure that you want to use this playlist name anyways ?")

                         if result == "NO":
                              return

          # if fileName wasn't provided from the command line arguments, prompt for it
          if fileName is None:
               # Prompt for the CSV to open. This will open the file for reading
               fileName,filter=QtGui.QFileDialog.getOpenFileName(self,'Choose the CSV to create the playlist from', selectedFilter='*.csv')

               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False
               
               print fileName
               
               if (fileName[-4:].upper() != ".CSV"):
                    self.messageBox("Create Playlist From Export","The file to create the playlist from must be a CSV file")
                    return
               
          try:
               # open the file for reading
               importFile=open(fileName,"r")
          except:
               print "An error occurred opening " + str(fileName)
               sys.exit()

          # read all lines from the file
          lines=importFile.readlines()

          # Verify the file selected by making sure that the first line of the CSV matches the playlist CSV header
          if lines[0]!=self.csvHeader:
               # When no command line arguments were provided, use MessageBox. Otherwise print the error message to the console
               if fileName is None:
                    self.messageBox("Create Playlist From Export","An error occurred reading the CSV that you selected. The header does not match")
                    return
               else:
                    print "An error occurred reading the CSV that you selected. The header does not match"
                    sys.exit()

          # Create the new playlist and store the new playlist id                 
          newPlaylistId=self.mc.create_playlist(newPlaylistName)

          # loop though all rows
          for num in range(1,len(lines)):
               # Strip the trailing newline from the current line
               currLine=lines[num].rstrip()

               # get everything up the first comma which is the track id
               firstDelim=currLine.find(chr(34) + ",")

               # add itto the new playlist
               self.mc.add_songs_to_playlist(newPlaylistId,currLine[1:firstDelim])

          # close the file
          importFile.close()

          if fileName is None:
               sys.exit()
          else:
               # Reload the playlists from the server
               self.loadPlaylists()

     # Event when the user clicks on a playlist that will be deleted     
     def deletePlaylist(self,playlistName,forceConfirmation=None):          
          # If no playlist name was provided at the command line, display confirmation twice before deleting the playlist
          if playlistName is None or forceConfirmation == True:
               # Confirm before deleting a playlist
               result=self.messageBox_YesNo("Delete Playlist", "Are you sure that you want to delete the playlist " + playlistName + " ?")

               if result != 'YES':
                    return
      
               # Confirm a 2nd time
               result=self.messageBox_YesNo("Delete Playlist", "Are you 100% sure that you want to delete the playlist " + playlistName + " ?")
                 
               if result != 'YES':
                    return

          # Get the playlist id for the specified playlist name
          for playlist in self.playlists:
               if playlist["name"]==playlistName:
                    deletePlaylistID=playlist["id"]
                      
          # API call to delete the playlist
          self.mc.delete_playlist(deletePlaylistID)
      
          # Reload the playlists from the server since we just deleted a playlist in case the user wants to delete another playlist
          if len(sys.argv) == 1:
               self.loadPlaylists()
          else:
               sys.exit()

     # Event when the user clicks on a playlist to be duplicated
     def duplicatePlaylist(self,playlistName,newPlaylistName=None,isRenaming=False):         
          # If no command line arguments were given, prompt for the name of the playlist to create
          if newPlaylistName is None:
               # Display the prompt modally
               newPlaylistName=self.showDialog("Duplicate a playlist","Please enter the name of the playlist that you want to create")
                 
               # When the dialog result is None, the user cancelled the dialog or clicked on OK without entering a playlist name
               if newPlaylistName == None or newPlaylistName == "":
                    return
      
          # If AllowDuplicatePlaylistNames is False, check to see if there is already a playlist with the same name as the one that will be created. If there is one, confirm with the user that they want to create a duplicate playlist
          if AllowDuplicatePlaylistNames==False:
               playlistNames=[]
                 
               # Add all playlist names to an array
               for playlist in self.playlists:
                    playlistNames.append(playlist["name"])
      
               # Sort the array
               allPlaylistNames=sorted(playlistNames)
      
               # Loop through all playlists. If the new playlist name chosen is in use, confirm with the user before creating a new playlist with the same name as another existing playlist
               for playlist in allPlaylistNames:
                    # Only display this message when we are not working from the command line. parseCommandLineArguments() will verify that the playlist doesn't exist already when using command line arguments
                    if playlist==newPlaylistName and newPlaylistName is None:
                         result=self.messageBox_YesNo("Playlist name exists already","The new playlist name that you entered exists already. Are you sure that you want to use this playlist name anyways ?")
      
                         if result != 'YES':
                              return
      
          # Create the new playlist and store the new playlist id                                                                           
          newPlaylistId=self.mc.create_playlist(newPlaylistName)
        
          # Loop through all tracks in the playlist and add each one to the new playlist
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         self.mc.add_songs_to_playlist(newPlaylistId,track['trackId'])
          
          # When isRenaming is True, delete the playlist after it has been duplicated
          if (isRenaming==True):
               # Get the playlist id for the specified playlist name
               for playlist in self.playlists:              
                    # Delete the original playlist
                    if playlist["name"]==playlistName:                              
                         # API call to delete the playlist
                         self.mc.delete_playlist(playlist["id"])
          
          # When a command line argument was passed terminate the application
          if len(sys.argv) > 1:
               sys.exit()
          else:
               # Reload the playlists from the server since we just deleted a playlist in case the user wants to delete another playlist
               self.loadPlaylists()

     # Event when the user clicks on Export All Playlists
     def exportAllPlaylists(self,exportPath=None,exportFormat=None):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat="CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return

          # If path wasn't given at the command line prompt for it
          if exportPath is None:
               exportPath=None
                 
               exportPath = QtGui.QFileDialog.getExistingDirectory(parent=self,dir="/",caption='Please select a directory')
      
               if exportPath == "" or exportPath is None:
                    return

          if sys.platform == "win32":
               exportPath=exportPath.replace("/","\\")
               delimiter="\\"
          else:
               delimiter="/"
      
          playlisttracks=[]
      
          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               # Replace any characters that are not allowed in Windows filenames with _.
               playlistname=playlist["name"].replace("/","_").replace("\\","_").replace(":","_").replace("*","_").replace("?","_").replace(":","_").replace(chr(34),"_").replace("<","_").replace(">","_").replace("|","_")
      
               currFile=open(exportPath + delimiter + playlistname + "." + exportFormat.lower(),"w")

               if exportFormat == "CSV":        
                    currFile.write(self.csvHeader)
               elif exportFormat == "HTML":
                    currFile.write(self.HTMLHeader)

               # write out the data for each track in the playlist
               for track in sorted(playlist["tracks"]):
                    currTrack=self.library[track['trackId']]
      
                    if exportFormat == "CSV":
                         currFile.write('"' + currTrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         currFile.write('"' + currTrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         currFile.write(str(currTrack[4]) + ',')
                         currFile.write(str(currTrack[5]) + ',')
                         currFile.write('"' + currTrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                         currFile.write(str(currTrack[7]) + ',')
                         currFile.write('"' + currTrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '"\n')
                    elif exportFormat == "HTML":
                         # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                         if (currTrack[0] == ""): currTrack[0]="&nbsp;"
                         if (currTrack[1] == ""): currTrack[1]="&nbsp;"
                         if (currTrack[2] == ""): currTrack[2]="&nbsp;"
                         if (currTrack[3] == ""): currTrack[3]="&nbsp;"
                         if (currTrack[4] == ""): currTrack[4]="&nbsp;"
                         if (currTrack[5] == ""): currTrack[5]="&nbsp;"
                         if (currTrack[6] == ""): currTrack[6]="&nbsp;"
                         if (currTrack[7] == ""): currTrack[7]="&nbsp;"
                         if (currTrack[8] == ""): currTrack[8]="&nbsp;"
                        
                         currFile.write("<TR>")
                         currFile.write("<TD>" + currTrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + currTrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         currFile.write("<TD>" + str(currTrack[4]) + "</TD>")
                         currFile.write("<TD>" + str(currTrack[5]) + "</TD>")
                         currFile.write("<TD>" + currTrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                              
                         currFile.write("<TD>" + str(currTrack[7]) + "</TD>")
                         currFile.write("<TD>" + currTrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + "</TD>")
                         currFile.write("</TR>\n")

               if exportFormat == "HTML":
                    currFile.write(self.HTMLFooter)

               currFile.close()
      
          if len(sys.argv) > 1:
               sys.exit()

     # Verify that the export format is valid
     def exportFormatIsValid(self,exportFormat):
          if exportFormat == "CSV" or exportFormat == "HTML":
               return True
          else:
               return False
               
     # Event when the user selects the export library option
     def exportLibrary(self,fileName=None,exportFormat=None):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat="CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return

          # If no filename was provided at the command line, prompt for one
          if fileName is None:            
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if (exportFormat=="CSV"):
                    fileName,filter=QtGui.QFileDialog.getSaveFileName(self,'Choose the location to save the export',"My GMusic Library as of " + time.strftime("%x").replace("/","-") + "." + exportFormat.lower(),"CSV (*.csv)")
               elif (exportFormat=="HTML"):
                    fileName,filter=QtGui.QFileDialog.getSaveFileName(self,'Choose the location to save the export',"My GMusic Library as of " + time.strftime("%x").replace("/","-") + "." + exportFormat.lower(),'HTML (*.html)')             
               
               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":
                    return False

          exportFile=open(fileName,"w")

          # Reference to entire catalog
          library = sorted(self.mc.get_all_songs())
                 
          librarySize=len(library)-1
                 
          # CSV Header
          if exportFormat == "CSV":
               exportFile.write(self.csvHeader)
          elif exportFormat == "HTML":
               exportFile.write(self.HTMLHeader)

          # Loop through all tracks
          for num in range(0,len(library)-1):
               # write CSV data
               if exportFormat == "CSV":
                    exportFile.write('"' + library[num]["id"] + '",')
                    exportFile.write('"' + library[num]["title"].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write('"' + library[num]["artist"].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write('"' + library[num]["album"].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write(str(library[num]["year"]) + ',')
                    exportFile.write('"' + library[num]["albumArtist"].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write(str(library[num]["trackNumber"]) + ',')
                    exportFile.write(str(library[num]["discNumber"]) + ',')
                    exportFile.write('"' + library[num]["genre"].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '"\n')
               elif exportFormat == "HTML":
                    # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                    if (library[num]["id"] == ""): library[num]["id"]="&nbsp;"
                    if (library[num]["title"] == ""): library[num]["title"]="&nbsp;"
                    if (library[num]["artist"] == ""): library[num]["artist"]="&nbsp;"
                    if (library[num]["album"] == ""): library[num]["album"]="&nbsp;"
                    if (library[num]["year"] == ""): library[num]["year"]="&nbsp;"
                    if (library[num]["albumArtist"] == ""): library[num]["albumArtist"]="&nbsp;"
                    if (library[num]["trackNumber"] == ""): library[num]["trackNumber"]="&nbsp;"
                    if (library[num]["discNumber"] == ""): library[num]["discNumber"]="&nbsp;"
                    if (library[num]["genre"] == ""): library[num]["genre"]="&nbsp;"

                    exportFile.write("<TR>")
                    exportFile.write("<TD>" + library[num]["id"] + "</TD>")
                    exportFile.write("<TD>" + library[num]["title"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + library[num]["artist"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + library[num]["album"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + str(library[num]["year"]) + "</TD>")
                    exportFile.write("<TD>" + library[num]["albumArtist"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("<TD>" + str(library[num]["trackNumber"]) + "</TD>")
                    exportFile.write("<TD>" + str(library[num]["discNumber"]) + "</TD>")
                    exportFile.write("<TD>" + library[num]["genre"].encode('utf-8').strip() + "</TD>")
                    exportFile.write("</TR>\n")
                        
     #         These 2 fields for play count and rating don't retrieve the values correctly and cause the script to crash
     #          exportFile.write(str(library[num]["playCount"]) + ',')
     #          exportFile.write('"' + library[num]["rating"].encode('utf-8').strip() + '"\n')
      
          if exportFormat == "HTML":
               exportFile.write(self.HTMLFooter)
              
          exportFile.close()
      
          if len(sys.argv) == 1:           
               self.messageBox("Export Library","Export complete")
          else:
               sys.exit()

     # Event when the user clicks on a playlist to export        
     def exportPlaylist(self,playlistName,fileName=None,exportFormat=None):
          # Default export format to CSV if not specified
          if exportFormat is None:
               exportFormat="CSV"
          elif self.exportFormatIsValid(exportFormat) != True:
               print "Export a playlist: Invalid exportFormat type " + exportFormat
               return

          # If a command line argument wasn't given prompt for the location to save the playlist
          if fileName is None:
               # Prompt for the location and filename to save the export using the playlistname.exportformat as the default file name
               if (exportFormat=="CSV"):
                    fileName,filter=QtGui.QFileDialog.getSaveFileName(self,'Choose the CSV to create the playlist from',playlistName + "." + exportFormat.lower(),'CSV (*.csv)')
               elif (exportFormat=="HTML"):
                    fileName,filter=QtGui.QFileDialog.getSaveFileName(self,'Choose the CSV to create the playlist from',playlistName + "." + exportFormat.lower(),'HTML (*.html)')
                    
               # If the user clicked on cancel then do nothing
               if fileName is None or fileName == "":                
                    return

          exportFile=open(fileName,"w")
      
          playlisttracks=[]

          # Loop through the playlist and add all tracks to playlisttracks array
          for playlist in self.playlists:
               if playlist["name"] == playlistName:
                    for track in sorted(playlist["tracks"]):
                         playlisttracks.append(self.library[track['trackId']])
      
          # Sort the playlist tracks by index 0 (The track name)
          playlisttracks=sorted(playlisttracks,key=lambda playlisttrack:playlisttrack[0])
      
          # Heading
          if exportFormat == "CSV":
               exportFile.write(self.csvHeader)
          elif exportFormat == "HTML":
               exportFile.write(self.HTMLHeader)

          # Playlist Data
          for playlisttrack in playlisttracks:
               if exportFormat == "CSV":
                    # All double quotation marks have to be replaced with "" to be parsed correctly as a CSV
                    exportFile.write('"' + playlisttrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write('"' + playlisttrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write(str(playlisttrack[4]) + ',')
                    exportFile.write(str(playlisttrack[5]) + ',')
                    exportFile.write('"' + playlisttrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '",')
                    exportFile.write(str(playlisttrack[7]) + ',')
                    exportFile.write('"' + playlisttrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34)) + '"\n')
               elif exportFormat == "HTML":
                    # When writing the file as HTML, replace any blanks with &nbsp so it will render correctly in the HTML table
                    if (playlisttrack[0] == ""): playlisttrack[0]="&nbsp;"
                    if (playlisttrack[1] == ""): playlisttrack[1]="&nbsp;"
                    if (playlisttrack[2] == ""): playlisttrack[2]="&nbsp;"
                    if (playlisttrack[3] == ""): playlisttrack[3]="&nbsp;"
                    if (playlisttrack[4] == ""): playlisttrack[4]="&nbsp;"
                    if (playlisttrack[5] == ""): playlisttrack[5]="&nbsp;"
                    if (playlisttrack[6] == ""): playlisttrack[6]="&nbsp;"
                    if (playlisttrack[7] == ""): playlisttrack[7]="&nbsp;"
                    if (playlisttrack[8] == ""): playlisttrack[8]="&nbsp;"
                        
                    exportFile.write("<TR>")
                    exportFile.write("<TD>" + playlisttrack[0].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[1].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[2].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[3].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[4])  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[5])  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[6].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("<TD>" + str(playlisttrack[7])  + "</TD>")
                    exportFile.write("<TD>" + playlisttrack[8].encode('utf-8').strip().replace(chr(34),chr(34)+chr(34))  + "</TD>")
                    exportFile.write("</TR>\n")

          if exportFormat == "HTML":
               exportFile.write(self.HTMLFooter)

          exportFile.close()
          
          # If this wasn't called from the command line argument, display a message that it has completed
          if fileName is None or fileName == "":
               self.messageBox("Export Library","Export complete")
          else:
               return
               
     # Event when the user clicks on the Export As ComboBox for a library task
     def libraryExportFormatComboBoxChange(self):
          if str(self.libraryTaskComboBox.currentText()) == "Export your entire library" and self.libraryExportFormatComboBox.currentIndex() != 0:
               self.exportLibrary(None,self.libraryExportFormatComboBox.currentText())
               self.resetLayout()
     
     # Event when the user chooses a library related task
     def libraryTaskComboBoxChange(self,optionItem):
          if optionItem == "Export your entire library":
               if self.libraryExportFormatComboBox.isHidden() == False and self.libraryExportFormatComboBox.currentIndex() != 0:
                    self.exportLibrary()
                    self.resetLayout()
               else:
                    self.libraryExportFormatLabel.show()
                    self.libraryExportFormatComboBox.show()
          elif optionItem == "View recently added files":
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
               self.library = {song['id']: [ song['id'],song['title'],song['album'],song['artist'],song['trackNumber'],song['year'],song['albumArtist'],song['discNumber'],song['genre'],song['creationTimestamp']] for song in self.mc.get_all_songs()}
          except:
               # When no command line arguments were provided, we are using the GUI so use MessageBox, otherwise print error message to console
               if ( len(sys.argv) == 1 ):
                    self.messageBox("Library Error","An error occurred while getting the list of songs in your library. Please try again")
               else:
                    print "An error occurred while getting the list of songs in your library. Please try again"
               sys.exit()

     # Load playlists and store values in the playlist ComboBox
     def loadPlaylists(self):
          self.playlists=self.mc.get_all_user_playlist_contents()
          
          playlistNames=[]
          
          for playlist in self.playlists:
               playlistNames.insert(0,playlist["name"])

          playlistNames.sort(key=lambda s: s.lower())
          
          self.playlistComboBox.clear()
         
          for playlist in playlistNames:
               self.playlistComboBox.addItem(playlist)

     # Display MessageBox with Ok button
     def messageBox(self,title,message):
          QtGui.QMessageBox.question(self,title,message, QtGui.QMessageBox.Ok)
          
          return True
	
     # Display MessageBox with Yes/No Buttons
     def messageBox_YesNo(self,title,message):
          reply=QtGui.QMessageBox.question(self,title,message,QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
     
          if reply==QtGui.QMessageBox.Yes:
               return "YES"
          else:
               return "NO"

     # Parse and validate command line arguments
     def parseCommandLineArguments(self):     
          validParameter=False
        
          # Command line arguments are the # of total parameters required including the app
          claParameters = { "/createplaylist" : 3,"/deleteplaylist" : 2,"/duplicateplaylist" : 3,"/exportplaylist": 4,"/exportallplaylists":3,"/exportlibrary":3,"/help": 1,"/recentlyadded":4,"/renameplaylist":3}
      
          # No command line arguments
          if ( len(sys.argv) <= 1 ):
               # Load all playlists
               self.playlists=self.mc.get_all_user_playlist_contents()
                        
               self.loadLibrary()

               return

          # Verify that the correct # of parameters were given. I start at index 1 and not 0 because index 0 referes to this script
          validParameter=False

          # loop through all parameters
          for key in claParameters:
               if key == sys.argv[1]:
                    validParameter=True
                 
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

          if sys.argv[1] == '/help':
               self.commandLineUsage()
          elif sys.argv[1] == "/createplaylist":
               self.playlists=self.mc.get_all_user_playlist_contents()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[2] and AllowDuplicatePlaylistNames==False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         self.commandLineUsage()
                         sys.exit()
               if (str(sys.argv[3])[-4:].upper() != ".CSV"):
                    print "The filename argument for /createplaylist must be a CSV file"
                    self.commandLineUsage()
                    sys.exit()
                
               self.createPlaylistFromCSV(sys.argv[2],sys.argv[3])
          elif sys.argv[1] == "/deleteplaylist":
               self.playlists=self.mc.get_all_user_playlist_contents()
             
               # Validate that the playlist name provided is valid
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[2]:
                         validPlaylist=True
            
               if validPlaylist==False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    self.commandLineUsage()
                    sys.exit()

               self.deletePlaylist(sys.argv[2])
          elif sys.argv[1] == "/duplicateplaylist":
               self.playlists=self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[2]:
                         validPlaylist=True
            
               if validPlaylist==False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    self.commandLineUsage()
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[3] and AllowDuplicatePlaylistNames==False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         self.commandLineUsage()
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2],sys.argv[3])
          elif sys.argv[1] == "/exportlibrary":
               # Convert the export format to upper case
               sys.argv[3]=sys.argv[3].upper()
               
               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print "The export format " + sys.argv[3] + " is not valid."
                    self.commandLineUsage()
                    sys.exit()
                   
               self.exportLibrary(sys.argv[2],sys.argv[3])
          elif sys.argv[1] == "/exportplaylist":   
               # Convert the export format to upper case
               sys.argv[4]=sys.argv[4].upper()
               
               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print "The export format " + sys.argv[4] + " is not valid."
                    self.commandLineUsage()
                    sys.exit()

               self.playlists=self.mc.get_all_user_playlist_contents()
            
               self.loadLibrary()

               # Validate Playlist
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[2]:
                         validPlaylist=True
            
               if validPlaylist==False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    self.commandLineUsage()
                    sys.exit()

               self.exportPlaylist(sys.argv[2],sys.argv[3],sys.argv[4])
          elif sys.argv[1] == "/exportallplaylists":
               # Convert the export format to upper case
               sys.argv[3]=sys.argv[3].upper()
               
               if self.exportFormatIsValid(sys.argv[3]) == False:
                    print "The export format " + sys.argv[3] + " is not valid."
                    self.commandLineUsage()
                    sys.exit()

               self.playlists=self.mc.get_all_user_playlist_contents()
            
               self.loadLibrary()
             
               self.exportAllPlaylists(sys.argv[2],sys.argv[3])
          elif sys.argv[1] == "/recentlyadded":
               # Convert the export format to upper case
               sys.argv[4]=sys.argv[4].upper()
               
               if self.exportFormatIsValid(sys.argv[4]) == False:
                    print "The export format " + sys.argv[4] + " is not valid."
                    self.commandLineUsage()
                    sys.exit()               
               
               try:
                    # This will raise ValueError if sys.argv[2] is not a valid date
                    asofDate=datetime.datetime.strptime(sys.argv[2], '%m/%d/%Y')
                    asofDate=asofDate.date()

                    # Load library
                    self.loadLibrary()

                    # Call the buildRecentlyAddedWindow() to save the fil
                    self.buildRecentlyAddedWindow(asofDate,sys.argv[3],sys.argv[4])
               except ValueError:
                    print "The recently added date " + sys.argv[2] + " is not valid"
                    sys.exit()
          elif sys.argv[1] == "/renameplaylist":
               self.playlists=self.mc.get_all_user_playlist_contents()

               # Validate that the playlist name provided is valid
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[2]:
                         validPlaylist=True
            
               if validPlaylist==False:
                    print "The playlist " + sys.argv[2] + " is not a valid playlist name for this account"
                    self.commandLineUsage()
                    sys.exit()

               # Validate that the new playlist name provided is not an existing playlist name
               validPlaylist=False

               for playlist in self.playlists:
                    if playlist["name"]==sys.argv[3] and AllowDuplicatePlaylistNames==False:
                         print "The new playlist name " + sys.argv[2] + " already exists. Please use /deleteplaylist first to delete the playlist"
                         self.commandLineUsage()
                         sys.exit()

               self.duplicatePlaylist(sys.argv[2],sys.argv[3],True)
                         
          sys.exit()

     # Event when the user chooses an item from the playlist ComboBox
     def playlistComboBoxChange(self):
          # These playlist tasks don't require the user to pick the export format
          if str(self.playlistTaskComboBox.currentText()) == "Delete a playlist":
               self.playlistExportFormatComboBox.hide()
               self.playlistExportFormatLabel.hide()
               self.deletePlaylist(str(self.playlistComboBox.currentText()),True)
          
               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Duplicate a playlist":
               print "here"
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
               self.duplicatePlaylist(str(self.playlistComboBox.currentText()),None,True)

               # Reset the layout
               self.resetLayout()
          else:
               # If the Playlist Export Format is already selected, trigger the event
               if self.playlistExportFormatComboBox.isHidden() == False and self.playlistExportFormatComboBox.currentIndex() != -1:
                    if str(self.playlistTaskComboBox.currentText()) == "Export a playlist":
                         self.exportPlaylist(playlistName=str(self.playlistComboBox.currentText()),exportFormat=self.playlistExportFormatComboBox.currentText())
                         
                         self.resetLayout()
                         return
                    elif  str(self.playlistTaskComboBox.currentText()) == "Export all playlists":
                         self.exportAllPlaylists(None,self.playlistExportFormatComboBox.currentText())
                         
                         self.resetLayout()
                    return
                    
               # Show Export As label and ComboBox
               self.playlistExportFormatLabel.show()
               self.playlistExportFormatComboBox.show()

     # Event when the user clicks on a format to export to
     def playlistExportFormatComboBoxChange(self):
          if str(self.playlistTaskComboBox.currentText()) == "Export a playlist":
               # If no playlist is selected, do nothing
               if self.playlistComboBox.currentIndex() == -1:
                    return
                    
               self.exportPlaylist(str(self.playlistComboBox.currentText()),None,str(self.playlistExportFormatComboBox.currentText()))
               
               # Reset the layout
               self.resetLayout()
          elif str(self.playlistTaskComboBox.currentText()) == "Export all playlists":
               self.exportAllPlaylists(None,str(self.playlistExportFormatComboBox.currentText()))
               
               # Reset the layout
               self.resetLayout()

     # Event when the user chooses a playlist related task
     def playlistTaskComboBoxChange(self,optionItem):     
          # If Delete a Playlist,Duplicate a Playlist or Export a Playlist is selected,show the playlist ComboBox and wait for the user to select a playlist
          # The only exception is Export all playlists which requires that the user select the export format
          if optionItem == "Delete a playlist" or optionItem == "Duplicate a playlist" or optionItem == "Export a playlist" or optionItem == "Reorder a playlist" or optionItem == "Rename a playlist":
               # Only this option from the ones above require the export format to be shown
               if optionItem == "Export a playlist": 
                    self.playlistComboBox.show()
                    self.playlistExportFormatLabel.show()

                    # unset and show Export as ComboBox
                    self.playlistExportFormatComboBox.setCurrentIndex(-1)
                    self.playlistExportFormatComboBox.show()
               
                    self.playlistLabel.show()                 
               else:
                    self.playlistExportFormatComboBox.hide()
                    self.playlistExportFormatLabel.hide()
               return
               
          elif optionItem == "Export all playlists":
               self.playlistLabel.hide()
               self.playlistComboBox.hide()
              
               self.playlistExportFormatLabel.show()
               
               self.resetLayout()

               return
          elif optionItem == "Create a playlist from CSV":
               self.createPlaylistFromCSV()
               self.loadPlaylists()
               
               self.resetLayout()               
          else: # Nothing selected
               self.resetLayout()

     # Event when the user selects a date in the recently added widget
     def recentlyAddedDateEditChange(self):
          # Use the values stored from the QDateEdit        
          self.recentlyAddedYear=self.recentlyAddedDateEdit.date().year()
     
          self.recentlyAddedMonth=self.recentlyAddedDateEdit.date().month()
     
          self.recentlyAddedDay=self.recentlyAddedDateEdit.date().day()
          
          # Reset the As of Label and QDateEdit controls after a date has been selected
          self.recentlyAddedLabel.hide()
          
          self.recentlyAddedDateEdit.hide()
                    
          self.libraryTaskComboBox.setCurrentIndex(-1) 
          
          # Display the window with the table
          self.buildRecentlyAddedWindow()
          
          return True

     # Event when the user enters a date into recently added using the keyboard
     def recentlyAddedDateEditKeypress(self):
          # Disable keyboard events since the event is automatically triggered as soon as the date changes even when the user hasn't finished entering a date
          PySide.QtCore.QEvent.ignore()
     
     # Reset the layout of the window 
     def resetLayout(self):
          self.playlistTaskComboBox.setCurrentIndex(-1)

          self.playlistLabel.hide()    
          self.playlistComboBox.setCurrentIndex(-1)
          self.playlistComboBox.hide()
          self.playlistExportFormatLabel.hide()
          self.playlistExportFormatComboBox.hide()
          
          self.libraryExportFormatLabel.hide()
          self.libraryExportFormatComboBox.hide()
          self.recentlyAddedDateEdit.hide()
          self.recentlyAddedLabel.hide()
          
          self.libraryTaskComboBox.setCurrentIndex(-1)    
          self.libraryExportFormatComboBox.setCurrentIndex(-1)    
          
     # Prompt the user and return the result
     def showDialog(self,title,promptText):
          # the result of user input. It is "" when user clicks on ok without entering anything or None when they cancel the dialog
          result=None
          
          text, ok = QtGui.QInputDialog.getText(self,title,promptText)
            
          if ok:
               return str(text)
          else:
               return None

app = QtGui.QApplication(sys.argv)

# If either one is blank or set to the defaults display login prompt
if username is None or username=="mygmailaddress@gmail.com" or password is None or password=="mypassword":
     # When login credentials aren't stored or set to defaults and command line arguments are being used, do not display login
     if len(sys.argv) > 1:
          print "Error: The login information is not stored. Please edit this script with your login information if you want to use command line arguments"
          sys.exit()
          
     l=Login();
    
     if l.exec_() == QtGui.QDialog.Accepted:
          auth=l.getCreds()
        
          gMusicUtility=GMusicUtility(auth[0],auth[1])
else:
     gMusicUtility=GMusicUtility(username,password)

sys.exit(app.exec_())