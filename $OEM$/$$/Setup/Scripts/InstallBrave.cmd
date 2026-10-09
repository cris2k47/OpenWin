@echo off

"%SYSTEMROOT%\Setup\Files\BraveBrowserStandaloneSetup.exe" /silent /install
copy /y "%SYSTEMROOT%\Setup\Files\initial_preferences" "%SYSTEMDRIVE%\Program Files\BraveSoftware\Brave-Browser\Application\"
