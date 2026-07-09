@echo off
cd /d "C:\Users\custouch\WorkBuddy\2026-07-09-17-02-19"
start "" "C:\Users\custouch\.workbuddy\binaries\python\versions\3.13.12\python.exe" "C:\Users\custouch\WorkBuddy\2026-07-09-17-02-19\wechat_cover_tool.py"
timeout /t 2 >nul
start "" http://localhost:8765
exit
