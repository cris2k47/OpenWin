@echo off

for %%A in (
    Clipchamp.Clipchamp
    Microsoft.BingNews
    Microsoft.BingSearch
    Microsoft.BingWeather
    Microsoft.Copilot
    Microsoft.GamingApp
    Microsoft.GetHelp
    Microsoft.MicrosoftSolitaireCollection
    Microsoft.MicrosoftStickyNotes
    Microsoft.OutlookForWindows
    Microsoft.PowerAutomateDesktop
    Microsoft.Todos
    Microsoft.Windows.DevHome
    Microsoft.WindowsAlarms
    Microsoft.WindowsCamera
    Microsoft.WindowsFeedbackHub
    Microsoft.WindowsSoundRecorder
    Microsoft.WindowsTerminal
    Microsoft.YourPhone
    MicrosoftCorporationII.MicrosoftFamily
    MicrosoftCorporationII.QuickAssist
    MicrosoftWindows.Client.WebExperience
    MicrosoftWindows.CrossDevice
    MSTeams
) do (
    for /f "tokens=9 delims=\" %%B in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Applications" ^| find /I "%%A_"') do (
        DISM /Online /NoRestart /Remove-ProvisionedAppxPackage /PackageName:%%B
    )
)
