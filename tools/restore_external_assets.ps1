# restore_external_assets.ps1 — copia los assets pesados desde local_data/ a sus rutas de trabajo.
# Uso:  powershell -ExecutionPolicy Bypass -File tools\restore_external_assets.ps1 [-IncludeData]
param([switch]$IncludeData)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$local = Join-Path $repo "local_data"

function Copy-Asset($src, $dstDir) {
    if (-not (Test-Path $src)) { Write-Warning "FALTA: $src"; return }
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    Copy-Item $src $dstDir -Force
    Write-Host "OK -> $dstDir"
}

# Imagenes del paper (necesarias para compilar el PDF completo)
$ov = Join-Path $local "paper_assets\overleaf_images"
foreach ($n in @("RW_trajectory_far_detection_g.JPG","RW_trajectory_starting_evasion_g.JPG",
                 "RW_trajectory_middle_evasion_g.JPG","RW_trajectory_exit_evasion_g.JPG",
                 "RW_trajectory_middle_rejoin_g.JPG","RW_trajectory_rejoin_g.JPG")) {
    foreach ($dst in @("paper\revision\Main\images")) {
        Copy-Asset (Join-Path $ov $n) (Join-Path $repo $dst)
    }
}

# Video S1
Copy-Asset (Join-Path $local "paper_assets\supplementary\Video_S1.mp4") (Join-Path $repo "paper\supplementary")

# Peso YOLO canonico
Copy-Asset (Join-Path $local "yolo\weights\yolo_unreal_unrealScene_v1_best_e23_2026-02-18.pt") (Join-Path $repo "src\weights")

if ($IncludeData) {
    Write-Host "Datos pesados ya viven en local_data (no requieren copia):"
    Write-Host "  local_data\evidence\pipeline_logs   (zero_trust completo)"
    Write-Host "  local_data\evidence\sitl_dataflash  (77 .BIN)"
    Write-Host "  local_data\tools\real_flight_replay (replay M_20_1RR)"
    Write-Host "  local_data\yolo                     (datasets+weights)"
}

Write-Host "Listo. Verifica sha256 contra external_data/HEAVY_EXTERNAL_MANIFEST.csv si lo necesitas."
