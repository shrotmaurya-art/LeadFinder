<#
.SYNOPSIS
    Creates a "LeadFinderAI" shortcut on the Desktop that launches
    start_leadfinder.bat.  Run once after cloning/deploying.

    Usage:
      powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

    The icon file (icon.ico) lives next to this script.  Replace it with
    any .ico you prefer — the shortcut will pick it up automatically.
    If no icon.ico exists, the shortcut will use the default .bat icon.
#>

$ScriptDir   = Split-Path -Parent $PSCommandPath
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."
$BatPath     = Join-Path $ScriptDir "start_leadfinder.bat"
$IconPath    = Join-Path $ScriptDir "icon.ico"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "LeadFinderAI.lnk"

if (-not (Test-Path $BatPath)) {
    Write-Error "start_leadfinder.bat not found at $BatPath"
    exit 1
}

$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath         = $BatPath
$shortcut.WorkingDirectory   = $ProjectRoot
$shortcut.Description        = "LeadFinderAI Dashboard"
if (Test-Path $IconPath) {
    $shortcut.IconLocation = $IconPath
}
$shortcut.Save()

Write-Host "Shortcut created: $ShortcutPath"
Write-Host "Working directory: $ProjectRoot"
Write-Host
Write-Host "Double-click LeadFinderAI on your Desktop to launch."
