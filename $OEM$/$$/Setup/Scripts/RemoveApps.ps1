$apps = @(
    'Clipchamp.Clipchamp'
    'Microsoft.BingNews'
    'Microsoft.BingSearch'
    'Microsoft.BingWeather'
    'Microsoft.Copilot'
    'Microsoft.GamingApp'
    'Microsoft.GetHelp'
    'Microsoft.MicrosoftSolitaireCollection'
    'Microsoft.MicrosoftStickyNotes'
    'Microsoft.OutlookForWindows'
    'Microsoft.PowerAutomateDesktop'
    'Microsoft.Todos'
    'Microsoft.Windows.DevHome'
    'Microsoft.WindowsAlarms'
    'Microsoft.WindowsCamera'
    'Microsoft.WindowsFeedbackHub'
    'Microsoft.WindowsSoundRecorder'
    'Microsoft.WindowsTerminal'
    'Microsoft.YourPhone'
    'MicrosoftCorporationII.MicrosoftFamily'
    'MicrosoftCorporationII.QuickAssist'
    'MicrosoftWindows.Client.WebExperience'
    'MicrosoftWindows.CrossDevice'
    'MSTeams'
)

Get-AppxProvisionedPackage -Online |
    Where-Object DisplayName -In $apps |
    ForEach-Object { Remove-AppxProvisionedPackage -Online -PackageName $_.PackageName }
