@echo off

"%SYSTEMROOT%\Setup\Files\Firefox Setup 157.0.1.exe" /S
xcopy "%SYSTEMROOT%\Setup\Files\Mozilla Firefox" "%SYSTEMDRIVE%\Program Files\Mozilla Firefox\" /E /I /Y /Q
rmdir /s /q "%SYSTEMROOT%\Setup\Files\Mozilla Firefox"
