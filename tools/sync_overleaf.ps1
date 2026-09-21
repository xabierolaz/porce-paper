# sync_overleaf.ps1 — publica el manuscrito canonico PORCE en Overleaf.
#
# Proyecto Overleaf: https://www.overleaf.com/project/6aa92339ca32e18a56ad4776
# Flujo: paper/revision/ -> local_data/overleaf/deploy/ -> commit -> pull --rebase -> push a Overleaf.
#
# SOLO se sincronizan los ficheros gestionados por este repo:
#   paper/revision/main.tex                      -> deploy/Main/correccion.tex
#   paper/revision/Main/references_main.bib      -> deploy/Main/references_main.bib
#   paper/revision/Definitions/*                 -> deploy/Definitions/*
#   paper/revision/Main/images/* + local_data/paper_assets/overleaf_images/*.JPG -> deploy/Main/images/*
# No toca Main/main.tex, Main/Feedback_xabi.tex ni Main/no_tocar_references_main.bib.
#
# Uso:  powershell -ExecutionPolicy Bypass -File tools\sync_overleaf.ps1 [-Compile]
#       -Compile  comprueba la compilacion local con latexmk antes de subir (aborta si falla).

param(
  [switch]$Compile
)

$ErrorActionPreference = "Stop"

$repo   = Split-Path -Parent $PSScriptRoot
$local  = Join-Path $repo "local_data"
$deploy = Join-Path $local "overleaf\deploy"
$src    = Join-Path $repo "paper\revision"
$assets = Join-Path $local "paper_assets\overleaf_images"
$remote = "https://git.overleaf.com/6aa92339ca32e18a56ad4776"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git no encontrado en PATH." }

if (-not (Test-Path (Join-Path $deploy ".git"))) {
  Write-Host "[sync_overleaf] Clonando Overleaf en $deploy ..."
  New-Item -ItemType Directory -Force -Path (Split-Path $deploy -Parent) | Out-Null
  & git clone -q $remote $deploy
  if ($LASTEXITCODE -ne 0) { throw "git clone de Overleaf fallo." }
  & git -C $deploy remote rename origin overleaf
}

Write-Host "[sync_overleaf] pull --rebase overleaf main ..."
& git -C $deploy pull --rebase -q overleaf main
if ($LASTEXITCODE -ne 0) { throw "pull --rebase overleaf fallo (conflicto): resuelvelo a mano en $deploy." }

Copy-Item -Force (Join-Path $src "main.tex") (Join-Path $deploy "Main\correccion.tex")
Copy-Item -Force (Join-Path $src "Main\references_main.bib") (Join-Path $deploy "Main\references_main.bib")
New-Item -ItemType Directory -Force -Path (Join-Path $deploy "Definitions") | Out-Null
Copy-Item -Force (Join-Path $src "Definitions\*") (Join-Path $deploy "Definitions\")
New-Item -ItemType Directory -Force -Path (Join-Path $deploy "Main\images") | Out-Null
Copy-Item -Force (Join-Path $src "Main\images\*") (Join-Path $deploy "Main\images\")
if (Test-Path $assets) { Copy-Item -Force (Join-Path $assets "*.JPG") (Join-Path $deploy "Main\images\") }

if ($Compile) {
  $latexmk = Get-Command latexmk -ErrorAction SilentlyContinue
  if (-not $latexmk) {
    Write-Warning "latexmk no encontrado: se omite la comprobacion local."
  } else {
    $build = Join-Path $local "overleaf\_build"
    Remove-Item -Recurse -Force $build -ErrorAction SilentlyContinue
    Write-Host "[sync_overleaf] Compilando Main/correccion.tex (latexmk) ..."
    Push-Location $deploy
    try {
      & latexmk -pdf -interaction=nonstopmode -outdir="$build" "Main\correccion.tex" | Out-Null
    } finally {
      Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { throw "La compilacion local fallo: NO se sube nada." }
    Remove-Item -Recurse -Force $build -ErrorAction SilentlyContinue
  }
}

& git -C $deploy add -A
$dirty = (& git -C $deploy status --porcelain)
if ($dirty) {
  $authorName = (& git -C $repo config user.name)
  $authorEmail = (& git -C $repo config user.email)
  if (-not $authorName) { $authorName = "PORCE" }
  if (-not $authorEmail) { $authorEmail = "porce@localhost" }
  & git -C $deploy -c user.name="$authorName" -c user.email="$authorEmail" commit -q -m "update"
  if ($LASTEXITCODE -ne 0) { throw "commit fallo en $deploy." }
} else {
  Write-Host "[=] Sin cambios en el deploy"
}

& git -C $deploy push -q overleaf main
if ($LASTEXITCODE -ne 0) { throw "push a Overleaf fallo." }

Write-Host "[OK] Overleaf actualizado: $remote"
