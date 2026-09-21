# bootstrap_ardupilot.ps1 — fetch the exact ArduPilot revision used for the PORCE SITL campaign.
#
# The previous workflow identified the firmware with a local tag ("AION-Orca-Alpha2-24357")
# that is not reproducible from a clean machine. This script pins the verified commit SHA
# instead, initializes submodules, and can build the SITL binary in WSL.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\bootstrap_ardupilot.ps1
#   powershell -ExecutionPolicy Bypass -File tools\bootstrap_ardupilot.ps1 -BuildSITL
#
# The checkout lives in local_data/ardupilot (outside Git; heavy).

param(
  [string]$RepoRoot = "",
  [string]$ArduPilotRoot = "",
  [string]$Commit = "26ac908b7058638796888bddb1a498becce7d3d7",
  [string]$Remote = "https://github.com/ArduPilot/ardupilot.git",
  [switch]$BuildSITL
)

$ErrorActionPreference = "Stop"

function Fail([string]$message, [int]$code = 1) {
  Write-Host "[bootstrap_ardupilot] ERROR: $message" -ForegroundColor Red
  exit $code
}

function Step([string]$message) {
  Write-Host "[bootstrap_ardupilot] $message"
}

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
  $RepoRoot = (Resolve-Path $RepoRoot).Path
}
if (-not $ArduPilotRoot) {
  $ArduPilotRoot = Join-Path $RepoRoot "local_data\ardupilot"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Fail "git is not available on PATH."
}

if (-not (Test-Path $ArduPilotRoot)) {
  Step "Cloning ArduPilot into $ArduPilotRoot ..."
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ArduPilotRoot) | Out-Null
  & git clone --filter=blob:none $Remote $ArduPilotRoot
  if ($LASTEXITCODE -ne 0) { Fail "git clone failed." }
} else {
  Step "Using existing checkout: $ArduPilotRoot"
}

Step "Fetching pinned commit $Commit ..."
& git -C $ArduPilotRoot fetch origin $Commit
if ($LASTEXITCODE -ne 0) { Fail "git fetch of $Commit failed." }

& git -C $ArduPilotRoot checkout --detach $Commit
if ($LASTEXITCODE -ne 0) { Fail "git checkout $Commit failed." }

$head = (& git -C $ArduPilotRoot rev-parse HEAD).Trim()
if ($head -ne $Commit) {
  Fail "HEAD is $head, expected $Commit."
}
Step "HEAD verified: $head"

Step "Initializing submodules ..."
& git -C $ArduPilotRoot submodule update --init --recursive
if ($LASTEXITCODE -ne 0) { Fail "git submodule update failed." }

if ($BuildSITL) {
  $builder = Join-Path $RepoRoot "tools\build_sitl_wsl.ps1"
  if (-not (Test-Path $builder)) { Fail "Missing builder: $builder" }
  Step "Building SITL in WSL ..."
  & $builder -RepoRoot $RepoRoot -ArduPilotRoot $ArduPilotRoot
  if ($LASTEXITCODE -ne 0) { Fail "SITL build failed." }
}

Step "ArduPilot ready at $ArduPilotRoot ($Commit)."
