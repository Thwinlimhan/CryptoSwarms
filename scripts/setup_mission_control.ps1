param(
  [string]$Target = "mission-control-upstream"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Target)) {
  git clone https://github.com/builderz-labs/mission-control.git $Target
}

Copy-Item "$Target\.env.example" "$Target\.env" -Force
Write-Host "Mission Control prepared at $Target"
Write-Host "Edit $Target\.env with secure AUTH/API values before production use."
