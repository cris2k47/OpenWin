@echo off
setlocal EnableDelayedExpansion

reg delete "HKLM\SOFTWARE\Microsoft\EdgeUpdate\ClientState\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /v "experiment_control_labels" /f /reg:32
reg add "HKLM\SOFTWARE\Microsoft\EdgeUpdateDev" /v "AllowUninstall" /t REG_SZ /d "" /f /reg:32

mkdir "%SYSTEMROOT%\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe"
type nul > "%SYSTEMROOT%\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe\MicrosoftEdge.exe"
copy /y "%SYSTEMROOT%\System32\cmd.exe" "%SYSTEMROOT%\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe\dllhost.exe"

for %%A in (UninstallString UninstallArguments) do (
    for /f "tokens=2,*" %%B in ('reg query "HKLM\SOFTWARE\Microsoft\EdgeUpdate\ClientState\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /v "%%A" /reg:32') do (
        set "%%A=%%C"
    )
)
if defined UninstallString (
    "%SYSTEMROOT%\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe\dllhost.exe" /c ""!UninstallString!" !UninstallArguments! --force-uninstall"
)

rmdir /s /q "%SYSTEMROOT%\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe"

rmdir /s /q "%ProgramFiles(x86)%\Microsoft\EdgeCore"
rmdir /s /q "%ProgramFiles(x86)%\Microsoft\Edge"

reg delete "HKLM\SOFTWARE\Microsoft\Active Setup\Installed Components\{9459C573-B17A-45AE-9F64-1857B5D58CEE}" /f
reg delete "HKLM\SOFTWARE\Microsoft\EdgeUpdate\ClientState\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /f /reg:32
reg delete "HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}" /f /reg:32
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Edge" /f /reg:32
