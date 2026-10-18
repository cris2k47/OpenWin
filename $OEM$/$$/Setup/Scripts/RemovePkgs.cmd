@echo off
setlocal EnableDelayedExpansion

for %%A in (
    Microsoft-Windows-OneDrive-Setup-Package
    Microsoft-Windows-OneDrive-Setup-WOW64-Package
) do (
    for /f "tokens=8 delims=\" %%B in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Packages" ^| find /I "%%A~"') do (
        set "PackageName=%%B"
    )
    reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Packages\!PackageName!\Owners" /f
    DISM /Online /NoRestart /Remove-Package /PackageName:!PackageName!
)
