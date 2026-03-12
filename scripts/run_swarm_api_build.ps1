param(
  [int]$MaxAttempts = 4,
  [int]$InitialBackoffSeconds = 8
)

$attempt = 1
$backoff = [Math]::Max(1, $InitialBackoffSeconds)

while ($attempt -le $MaxAttempts) {
  Write-Host "[swarm-api-build] Attempt $attempt/$MaxAttempts"
  docker compose build --progress=plain swarm-api
  if ($LASTEXITCODE -eq 0) {
    Write-Host "[swarm-api-build] Build succeeded."
    exit 0
  }

  if ($attempt -eq $MaxAttempts) {
    break
  }

  Write-Host "[swarm-api-build] Build failed. Retrying in $backoff seconds..."
  Start-Sleep -Seconds $backoff
  $attempt += 1
  $backoff = [Math]::Min(90, $backoff * 2)
}

Write-Error "[swarm-api-build] Build failed after $MaxAttempts attempts."
exit 1
