param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

video-edit validate $ManifestPath
video-edit plan $ManifestPath $OutputPath
video-edit assemble $ManifestPath $OutputPath
