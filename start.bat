@echo off
rem ClawdPet - double-click to start the desktop pet. Original work: Miaomiao (GitHub: Miaomiaomeowmeow), CC BY-NC-SA 4.0
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw -3 clawd_pet.py
  goto end
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw clawd_pet.py
  goto end
)
echo.
echo   Python was not found on this computer.
echo   1. Download it from https://www.python.org/downloads/
echo   2. When installing, tick "Add python.exe to PATH"
echo   3. Double-click start.bat again
echo.
pause
:end
