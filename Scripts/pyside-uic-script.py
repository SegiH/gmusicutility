#!python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'PySide==1.2.2','console_scripts','pyside-uic'
__requires__ = 'PySide==1.2.2'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('PySide==1.2.2', 'console_scripts', 'pyside-uic')()
    )
