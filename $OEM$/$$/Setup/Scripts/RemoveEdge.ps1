$clientState = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\ClientState\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}'
Remove-ItemProperty -Path $clientState -Name 'experiment_control_labels' -ErrorAction SilentlyContinue

$edgeUpdateDev = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdateDev'
if (-not (Test-Path $edgeUpdateDev)) {
    New-Item -Path $edgeUpdateDev | Out-Null
}
Set-ItemProperty -Path $edgeUpdateDev -Name 'AllowUninstall' -Value '' -Type String

$systemApps = "$env:SystemRoot\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe"
New-Item -ItemType Directory -Path $systemApps -Force | Out-Null
New-Item -ItemType File -Path "$systemApps\MicrosoftEdge.exe" -Force | Out-Null
Copy-Item -Path "$env:SystemRoot\System32\cmd.exe" -Destination "$systemApps\dllhost.exe" -Force

$uninstall = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Edge' -ErrorAction SilentlyContinue).UninstallString
if ($uninstall) {
    Start-Process -FilePath "$systemApps\dllhost.exe" -ArgumentList "/c `"$uninstall --force-uninstall`"" -NoNewWindow -Wait
}

Remove-Item -Path $systemApps -Recurse -Force
