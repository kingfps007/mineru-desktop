@echo off
cd /d "%~dp0"
call %USERPROFILE%\.conda\envs\MinerU\python.exe scripts\mineru_cli.py
pause
