param(
  [int]$MaxAttempts = 5,
  [int]$InitialBackoffSeconds = 8
)

function Invoke-ComposeBuild([string]$Service) {
  docker compose build --progress=plain $Service
  return $LASTEXITCODE
}

function Invoke-ComposeBuildNoBuildKit([string]$Service) {
  $env:DOCKER_BUILDKIT = "0"
  try {
    docker compose build --progress=plain $Service
    return $LASTEXITCODE
  } finally {
    Remove-Item Env:DOCKER_BUILDKIT -ErrorAction SilentlyContinue
  }
}

Write-Host "[mission-control-build] Pre-pulling base image node:20-slim..."
docker pull node:20-slim | Out-Host

$attempt = 1
$backoff = [Math]::Max(1, $InitialBackoffSeconds)

while ($attempt -le $MaxAttempts) {
  Write-Host "[mission-control-build] Attempt $attempt/$MaxAttempts (BuildKit on)"
  $code = Invoke-ComposeBuild -Service "mission-control"
  if ($code -eq 0) {
    Write-Host "[mission-control-build] Build succeeded."
    exit 0
  }

  Write-Host "[mission-control-build] BuildKit build failed (exit $code). Trying fallback builder (DOCKER_BUILDKIT=0)..."
  $fallbackCode = Invoke-ComposeBuildNoBuildKit -Service "mission-control"
  if ($fallbackCode -eq 0) {
    Write-Host "[mission-control-build] Fallback build succeeded."
    exit 0
  }

  if ($attempt -eq $MaxAttempts) {
    break
  }

  Write-Host "[mission-control-build] Build failed. Retrying in $backoff seconds..."
  Start-Sleep -Seconds $backoff
  $attempt += 1
  $backoff = [Math]::Min(120, $backoff * 2)
}

Write-Error "[mission-control-build] Build failed after $MaxAttempts attempts."
exit 1
