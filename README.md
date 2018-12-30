gMusicUtility is a Python based app that lets you do things with your Google Play Music Library that you wouldn't be able to do otherwise. 
This app wouldn't be possible without this unofficial Google Play Music API available at https://github.com/simon-weber/gmusicapi developed by Simon Weber. 

gMusicUtility was created in Python and can run on Windows, Macs and Linux.

This app currently supports the following features:
     Save files on your local computer or DropBox
     Create a playlist on GPM based on a playlist CSV that was previously created using this app
     Delete a playlist
     Download all songs in a playlist as mp3 to your local computer or to your DropBox account
     Duplicate a playlist
     Export a list of all tracks in a playlist as CSV or HTML and save the exported playlist file locally or to your DropBox account
     Export all playlists as CSV or HTML and save playlist files locally or to your DropBox account
     Find Duplicate Tracks in Playlist: Compare 2 playlists and create CSV with tracks that are in both playlists
     Rename a playlist

     Export a list of all purchased songs in your GPM library as CSV or HTML and save file locally or DropBox.
     Export a list of all songs in your GPM library as CSV or HTML and save file locally or DropBox.
     View recently added music - Pick and date and see all tracks added since that date. Results can be saved as CSV
     Automatically checks for updates when using the UI (You can use /checkforupdates to check for an update from the command line) 

     Command line arguments to perform all of the above steps automatically from the command line.

Build Instructions
------------------
This app is available as native binaries for Windows and Mac or as a Python script which can be run easily on Windows, Mac and Linux.

If you do not want to use the native binaries for your operating system and want to manually run the Python script, 
you need to follow the instructions below.

1. Windows and Mac users: Install Python. This app will only work Python 3 or with Python 2 and the package PySide2 installed (Installing PySide2 is a hit or miss in Python 2).
   Python can download be from here https://www.python.org/downloads/ The latest version is 3.7.2. Choose the right installer for your O.S.
   
   Linux users: Python 2 or 3 should be installed already on most Linux distribution and shouldn't need to be manually installed.

   Windows users: If are on Windows 64 bit, you will want to get the download that says Windows x86-64 executable installer I don't recommend the zip because pip isn't provided in the zip and I had some issues trying to manually install pip.
   
   Windows users: When you run the Python Windows 64 bit installer,
        a. Check "Add Python 3.7 to PATH" 
        b. Choose Customize Installation Everything on this screen is checked by default. Leave it alone and click on Next.
        c. IMPORTANT! Change the Customize Install Location: to C:\Python37 or another easy to access directory.
        d. Install Python.

2. Once Python finishes installing, open up a command prompt/terminal. 
     a. Windows users:  Change to the directory where you installed Python. If you installed Python in C:\Python37 type cd C:\Python37\

3. Mac Users: Before continuing, you need to follow 2 more steps
     a. Open a terminal and run the command xcode-select --install When the window opens, click on Install to install the command line tools.
     b. You also need to download a python package called six from here https://pypi.org/project/six/#files download the latest version, extract the file and run python setup.py install in the extracted folder before continuing. Macs come with an older version of Python that comes with with an older version of the six package that won't work.

4. Make sure Python is working by running the command "python --version" without quotation marks. You should see something like Python 3.7.1 displayed.
5. Run the command pip --version. Windows users may need to run this command as scripts\pip --version. It should show something like this:
   pip 18.1 from c:\python37\lib\site-packages\pip (python 3.7)

6. If everything above worked, its time to install some Python packages. 
   Type "scripts\pip install <package name>" without the quotation marks and substitute <package name> for each of these packages below:
          a. dropbox 
          b. gmusicapi 
          c. mutagen 
          d. pyaes 
          e. PySide2
          f. requests
          g. Slugify
      
      Note: Run this command exactly like this: pip install dropbox gmusicapi mutagen pyaes PySide2
            to install all of the packages at once or you can did pip install package1 pip install package2 etc.
           ​ 
   All of the packages above need to install correctly for this to work.

7. Windows users: Save gMusicUtility.py to the Python directory
8. Run python GMusicUtility40.py
9. If you see a warning message when you run my app that says "/Library/Python/2.7/site-packages/gmusicapi/__init__.py:4: GmusicapiWarning: gmusicapi.clients.OAUTH_FILEPATH is deprecated and will be removed; use Musicmanager.OAUTH_FILEPATH"
and you want to hide this message from appearing every time that you run my app, it is possible to do so. If the path mentioned above without the file name is /Library/Python/2.7/site-packages/gmusicapi/ you need to go to the folder /Library/Python/2.7/site-packages/gmusicapi/clients (Note the clients sub folder at the end) and edit __init__.py in this script. The last line should say warnings.warn(msg, GmusicapiWarning, stacklevel=2) Add a # at the beginning of the line and save the file.
10. On Windows, if you get an error when you run this app that says "ImportError: DLL load failed: The specified module could not be found"
    search for Visual C++ Redistributables for Visual Studio 2015. There are later versions available. I am using 2015. 

Usage
-----
The first time that you run the application, it will automatically open up a page on Google that uses Google OAuth to securely authorize my app to access your Google Play Music account without providing your username or password to this app. 

Once you authorize my app on the Google web page, copy the code that Google gives you, go to the command prompt/terminal where you ran my app and paste the code. 

If you want to use the feature Download all songs in a playlist, you will have to complete the OAuth authorization a second time because it requires a separate authorization.

The same thing goes when you want to save a file to DropBox. You will need to complete DropBox OAuth the first time you try to save something to DropBox, Once you complete this for the first time, you won't have to do it again.

Once you have completed Google or DropBox OAuth for the first time, you'll never need to do it again as long as you don't delete the Oauth file which has the extension .cred.
Important note: If you want to send this app to someone, do not share any files with the extension .cred. The cred file is tied to your Google/DropBox account. Do not share this file with anyone. 

All of the stuff that you see in the GUI can be automated from the command line. Run python gmusicutility40.py /help and it will print out all of the command line arguments with examples.

Options & Customization
-----------------------
Some of the features that this app uses can be customized by editing gMusicUtility.py and changing the appropriate variables. 
Do not change anything below the line that says ### DO NOT EDIT ANYTHING BELOW THIS LINE

checkForUpdates = True - Change to False to disable automatic update checking

tableForegroundColor - Change HTML table foreground color. Color must be provided as hexadecimal. Ex: tableForegroundColor = "#000000" will set the foreground color to black

tableBackgroundColor - Change HTML table background color. Color must be provided as hexadecimal. Ex: tableBackgroundColor = "#FFFFFF" will set the background color to white

AllowDuplicatePlaylistNames - Set value to "True" to allow you to create a playlist even though there is already a playlist with the same name. This is false by default because it can be confusing to have 2 playlists with the same name

noM3U - Set value to "True" to prevent an m3u file from being created when downloading all songs in a playlist

noSubDirectories - Set value to True to prevent sub directories from being created when downloading all songs in a playlist.

Native application
------------------
If you want to, you can create a native application (I.E an Exe on Windows, a Mac binary for Mac or a native Linux binary) for your operating system
to create the same binaries made available on my Github page by following these steps: (Note: You can only create binaries for the platform that you are on. So if you are on Windows you can only create exe.)
     1. Install pyinstaller using pip: pip install pyinstaller
     2. Run pyinstaller gMusicUtility40.py (Windows users need to type scripts\pyinstaller) and wait. This still waill take about a minute.
     3. cd dist/gMusicUtility40 and run ./gmusicutility40. If you have already logged into Google and/or DropBox before, copy all the files with the extension cred into this directory.

Known issues
------------
1. If you try to cancel before completing the OAuth session, you have to Ctrl C to end the script. Sometimes you have to force quit the command prompt/terminal.
2. If you see an error "Could not find a suitable TLA CA certificate bundle, Invalid Path", you are missing the file cacert.pem. Download this file from my Github 
   page and put it in the same folder as the gMusicUtility binary. 
3. I have seen an issue that comes from Google's side when logging in that says "HTTPSConnectionPool(host='mclients.googleapis.com', port=443): Max retries exceeded with url:   
   /sj/v2.5/config?hl=en_US&dv=0&tier=fr (Caused by SSLError(SSLError(0, 'unknown error (_ssl.c:4045)')))" This is how Google limits a lot of connections from the same IP Address. Do not keep trying to log in again. Wait and try again later.
4. If you see an error that says dropbox.exceptions.AuthError: AuthError('ff3ffd437a309af8d75f923e4d8e21f2', AuthError(u'invalid_access_token', None)), delete DropBoxOAuth.cred and    
   authorize DropBox again.
5. When specifying a path when using the command line arguments, use an absolute path (especially on Linux) like /home/someusers/Desktop/allplaylists instead of a relative path like 
   ./allplaylists because relative paths cause an issue when downloading all songs in a playlist where the m3u file might not be generated.