@echo off
echo Running Gazedeck Console Executable...
echo =====================================
echo.
cd /d "%~dp0"
dist\GazedeckConsole\GazedeckConsole.exe
echo.
echo =====================================
echo Executable finished. Press any key to close this window.
pause >nul
