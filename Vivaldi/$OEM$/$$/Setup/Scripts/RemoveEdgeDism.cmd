@echo off

taskkill /f /im msedge.exe

rmdir /s /q "%ProgramFiles(x86)%\Microsoft\EdgeCore"
rmdir /s /q "%ProgramFiles(x86)%\Microsoft\Edge"

reg delete "HKLM\SOFTWARE\Microsoft\Active Setup\Installed Components\{9459C573-B17A-45AE-9F64-1857B5D58CEE}" /f
reg delete "HKLM\SOFTWARE\Microsoft\EdgeUpdate\ClientState\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /f /reg:32
reg delete "HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /f /reg:32
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Edge" /f /reg:32
