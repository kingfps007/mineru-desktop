@echo off
cd /d "%~dp0"
echo MinerU CLI v4.0.1
echo.
for %%d in ("%USERPROFILE%\.conda\envs\MinerU" "C:\ProgramData\miniconda3\envs\MinerU") do (
    if exist "%%~d\python.exe" (
        "%%~d\python.exe" "%~dp0scripts\mineru_cli.py"
        exit /b
    )
)
echo MinerU conda environment not found!
pause
