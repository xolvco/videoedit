param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath
)

$ErrorActionPreference = "Stop"

$json = video-edit probe $InputPath | Out-String
$media = $json | ConvertFrom-Json

Write-Host "Container:" $media.format.format_name
Write-Host "Duration:" $media.format.duration

