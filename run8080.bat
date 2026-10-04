@echo off
cd /d C:\Users\meimo\Desktop\StudyBuddy
set GIN_MODE=release
dist\studybuddy.exe >> data\server8080.log 2>&1
