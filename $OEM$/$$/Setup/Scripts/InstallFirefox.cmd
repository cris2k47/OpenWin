@echo off

"%SYSTEMROOT%\Setup\Files\Firefox Setup 157.0.1.exe" /S
move /y "%SYSTEMROOT%\Setup\Files\Mozilla Firefox" "%SYSTEMDRIVE%\Program Files\"
