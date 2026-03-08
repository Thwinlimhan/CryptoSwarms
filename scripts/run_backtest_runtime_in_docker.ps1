param(
  [string]$Image = "python:3.11-slim"
)

$ErrorActionPreference = "Stop"
$repo = "C:/workspace"

$cmd = @(
  "python -m pip install --upgrade pip",
  "pip install -e .[backtest] pytest",
  "export REQUIRE_BACKTEST_RUNTIMES=true",
  "pytest -q tests/integration/test_vectorbt_integration.py tests/integration/test_jesse_integration.py"
) -join " && "

docker run --rm -t -v "${PWD}:$repo" -w $repo $Image bash -lc $cmd
