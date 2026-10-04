@echo off
cd /d C:\Users\meimo\Desktop\StudyBuddy
set GIN_MODE=release
set STUDYBUDDY_PORT=8658
dist\studybuddy.exe >> data\server8658.log 2>&1
