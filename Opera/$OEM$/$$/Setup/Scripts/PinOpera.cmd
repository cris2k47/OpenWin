@echo off

rem Opera names its Start menu shortcut in the language of Windows, such as
rem "Opera Browser" or "Navegador Opera". Pin it by that name in the Start menu
rem and taskbar layouts of new users, which use "Opera Browser.lnk".
powershell -NoProfile -Command "$Shell = New-Object -ComObject WScript.Shell; $Opera = Join-Path $env:ProgramFiles 'Opera\opera.exe'; $Link = Get-ChildItem (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\*.lnk') | Where-Object { $Shell.CreateShortcut($_.FullName).TargetPath -eq $Opera } | Select-Object -First 1; if ($Link) { foreach ($File in 'LayoutModification.json', 'LayoutModification.xml') { $Path = Join-Path $env:SystemDrive ('Users\Default\AppData\Local\Microsoft\Windows\Shell\' + $File);[IO.File]::WriteAllText($Path, [IO.File]::ReadAllText($Path).Replace('Opera Browser.lnk', $Link.Name)) } }"
