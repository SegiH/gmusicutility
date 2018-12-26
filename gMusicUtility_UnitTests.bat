@echo off
SETLOCAL enableextensions enabledelayedexpansion

REM Store all unit test names in pseudo array so we can loop over them
SET CLA[0]=createplaylistfromcsv
SET CLA[1]=deleteplaylist
SET CLA[2]=downloadallsongs_local
SET CLA[3]=downloadallsongs_dropbox
SET CLA[4]=deleteplaylist
SET CLA[5]=downloadallsongs_local 
SET CLA[6]=downloadallsongs_dropbox
SET CLA[7]=duplicateplaylist 
SET CLA[8]=exportplaylist_locally_csv 
SET CLA[9]=exportplaylist_locally_html 
SET CLA[10]=exportplaylist_dropbox_csv 
SET CLA[11]=exportplaylist_dropbox_html
SET CLA[12]=findduplicates_locally
SET CLA[13]=findduplicates_dropbox
SET CLA[14]=recentlyadded_locally_csv
SET CLA[15]=recentlyadded_locally_html
SET CLA[16]=recentlyadded_dropbox_csv 
SET CLA[17]=recentlyadded_dropbox_html
SET CLA[18]=renameplaylist

IF NOT "%1" == "" (
     REM Loop through all available unit tests
     FOR /L %%C IN (0,1,99) DO (
          REM If the current array element is empty, we've reached the end. This is done this way so we don't have to hard code the size of the array
          IF "!CLA[%%C]!" == "" (
		       goto end
	      )
	 
	      REM If the current item is the one we are looking for, jump to that test
          IF "!CLA[%%C]!" == "%1" goto %1
     )

     GOTO end
)

cd\python37

echo gMusicUtility Unit Tests. Press any key to begin running all tests
pause

:createplaylistfromcsv
REM Create playlist from CSV
REM python gMusicUtility40.py gMusicUtility40.py /createplaylist BS-fromCSV BS.csv
REM echo Check GPM and make sure that the playlist
REM pause

REM IF "%2" == "downloadallsongs_local" goto end


:deleteplaylist
echo Unit Test: Delete Playlist 
python gMusicUtility40.py /deleteplaylist BS2
echo Check GPM to see if the playlist BS2 was deleted. If it was, this unit test passed. Refresh GPM if its already open.
pause

IF "%2" == "deleteplaylist" goto end

:downloadallsongs_local
echo Unit Test: Download all songs in a playlist Locally
mkdir allPlaylists
del /Q allPlaylists\*.*
python gMusicUtility40.py /downloadplaylist BS allPlaylists
dir allPlaylists
echo If you see all of the GPM playlists in the directory listing above, this unit test passed.
pause

IF "%2" == "downloadallsongs_local" goto end


:downloadallsongs_dropbox
echo Unit Test: Download all songs in a playlist DropBox
python gMusicUtility40.py /downloadplaylist BS DropBox
echo Check DropBox and make sure that you see all of the playlists there. If you do, this unit test passed.
pause

IF "%2" == "downloadallsongs_dropbox" goto end


:duplicateplaylist
echo Unit Test: Duplicate a playlist.
python gMusicUtility40.py /duplicateplaylist BS BS-duplicate
echo Check GPM to see if the playlist BS was duplicated as BS-duplicate. If it was, this unit test passed. Refresh GPM if its already open.
pause

IF "%2" == "duplicateplaylist" goto end


:exportplaylist_locally_csv
echo Unit Test: Export a playlist Locally CSV
IF EXIST BS.CSV DEL BS.csv
gMusicUtility40.py /exportplaylist BS BS.csv CSV
explorer BS.csv
echo If this CSV opened and looks correct, this unit test passed.
pause

IF "%2" == "exportplaylist_locally_csv" goto end


:exportplaylist_locally_html
echo Unit Test: Export a playlist Locally HTML
IF EXIST BS.html DEL BS.html
gMusicUtility40.py /exportplaylist BS BS.html HTML
explorer BS.html
echo If this HTML file opened and looks correct, this unit test passed
pause

IF "%2" == "exportplaylist_locally_html" goto end


:exportplaylist_dropbox_csv
echo Unit Test: Export a playlist DropBox CSV
gMusicUtility40.py /exportplaylist BS Dropbox CSV
echo Check DropBox and make sure that BS.csv is there. If it is, this unit test passed
pause

IF "%2" == "exportplaylist_dropbox_csv" goto end


:exportplaylist_dropbox_html
echo Unit Test: Export a playlist DropBox HTML
gMusicUtility40.py /exportplaylist BS Dropbox HTML
echo Check DropBox and make sure that BS.html is there. If it is, this unit test passed
pause

IF "%2" == "exportplaylist_dropbox_html" goto end


:findduplicates_locally
echo Unit Test: Find Duplicates Locally
IF EXIST DEL Rock_Misc_Comparison.csv
gMusicUtility40.py /findduplicates BS BS-duplicate Rock_Misc_Comparison.csv
explorer Rock_Misc_Comparison.csv
echo If Rock_Misc_Comparison.csv opened and looks correct, this unit test passed
pause

IF "%2" == "findduplicates_locally" goto end


:findduplicates_dropbox
echo Unit Test: Find Duplicates DropBox
gMusicUtility40.py /findduplicates BS BS-duplicate Dropbox
echo Check DropBox and make sure that BS to BS2 Comparison.csv is there and looks correct. If it does, this unit test passed
pause

IF "%2" == "findduplicates_dropbox" goto end


:recentlyadded_locally_csv
echo Unit Test: Recently Added: Locally CSV
IF EXIST recentlyadded.csv DEL recentlyadded.csv
gMusicUtility40.py /recentlyadded 11/01/2018 recentlyadded.csv CSV
explorer recentlyadded.csv
echo If recentlyadded.csv opened and looks correct, this unit test passed
pause

IF "%2" == "recentlyadded_locally_csv" goto end


:recentlyadded_locally_html
echo Unit Test: Recently Added: Locally HTML
IF EXIST recentlyadded.html DEL recentlyadded.html
gMusicUtility40.py /recentlyadded 11/01/2018 recentlyadded.html HTML
explorer recentlyadded.html
echo If recentlyadded.html opened asnd looks correct. If it did, this unit test passed
pause

IF "%2" == "recentlyadded_locally_html" goto end

:recentlyadded_dropbox_csv
echo Unit Test: Recently Added: DropBox CSV
gMusicUtility40.py /recentlyadded 11/01/2018 Dropbox CSV
echo Check DropBox and make sure that recentlyadded.csv is there and looks correct. If it did, this unit test passed
pause

IF "%2" == "recentlyadded_dropbox_csv" goto end


:recentlyadded_dropbox_html
echo Unit Test: Recently Added: DropBox HTML
gMusicUtility40.py /recentlyadded 11/01/2018 Dropbox HTML
echo Check DropBox and make sure that recentlyadded.html is there and looks correct. If it did, this unit test passed
pause

IF "%2" == "recentlyadded_dropbox_html" goto end


:renameplaylist
echo Unit Test: Rename a playlist
gMusicUtility40.py /renameplaylist BS BS-NEW
echo Check GPM to see if the playlist BS was renamed to BS-NEW. If it did, this unit test passed. Refresh GPM if its already open
pause

IF "%2" == "renameplaylist" goto end


echo Done!
:end
ENDLOCAL