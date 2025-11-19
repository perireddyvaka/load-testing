param(
    [string]$Host = "http://10.2.16.116:8610",
    [string]$LocustArgs = ""
)

# Activate venv (PowerShell). Adjust path if your venv is elsewhere.
$venvActivate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment activate script not found at: $venvActivate`nCreate/restore the venv or adjust this script."
    exit 1
}

Write-Host "Activating virtual environment..."
& $venvActivate

# Ensure python from the venv is used
$py = & python -c "import sys,sysconfig; print(sys.executable)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Unable to run python from this environment. Make sure the venv activation succeeded."
    exit 1
}
Write-Host "Using python: $py"

# Check if locust is installed in the venv; if not install it
python - <<'PY'
import pkgutil,sys
if pkgutil.find_loader("locust"):
    sys.exit(0)
else:
    sys.exit(1)
PY
if ($LASTEXITCODE -ne 0) {
    Write-Host "Locust not found in venv. Installing locust..."
    pip install locust
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install locust in the virtualenv."
        exit 1
    }
}

# Run locust via python -m locust so we don't rely on the 'locust' exe being on PATH
Write-Host "Launching locust (file: py.py) -- host: $Host"
& python -m locust -f (Join-Path $PSScriptRoot "py.py") --host=$Host $LocustArgs
