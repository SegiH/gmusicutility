@echo off
REM cd Scripts
Scripts\pylint.exe -d C0301 -d W0311 -d W1401 -d C0302 -d E0222 -d CO103 -d E0602 -d invalid-name -d no-member -d multiple-statements -d missing-docstring gMusicUtility26.py > out.txt