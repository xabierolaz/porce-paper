# PORCE — repo canónico (paper + experimentos reproducibles)

Único documento de entrada del repositorio. Remoto **público**:
`github.com/xabierolaz/porce-paper`. Estado: 21/09/2026.

PORCE (static-obstacle paper, clase *Electronics*, en major revision) se revisa aquí junto
con su runtime reproducible. Los documentos internos de auditoría/planificación están archivados fuera de Git
(`local_data/planning/20260921/`); solo quedan como documentos separados dos entregables
con función propia:

- `evidence/field/README.md` — acta de campaña de los vuelos físicos PF1/PF2/PF3.
- `review/response_to_reviewers.md` — respuesta operativa a los 52 comentarios (el verbatim
  del feedback vive en `local_data/planning/20260921/review/`).

## 1. Estado actual

- **Manuscrito canónico**: `paper/revision/main.tex` (copia verbatim del original de trabajo del
  autor; SHA-256 en `paper/revision/MANUSCRIPT_PROVENANCE.json`). Los snapshots previos
  (`electronics_v4/`, `submitted_mdpi_v1/`) quedaron fuera de Git: solo hay un manuscrito
  activo y un baseline inmutable.
- **Baseline de submission inmutable**: `paper/submitted/` con las fuentes exactas de los dos
  ZIP de agosto de 2026 y `SUBMISSION_MANIFEST.json` (SHA-256 de cada entrada). Los ZIP
  originales viven en `local_data/evidence/submission_zips/`.
- **Campaña simulada del paper verificada**: la tabla se recomputa 1:1 y las 3 figuras
  cuantitativas regeneran bit-exactas desde los logs archivados.
- **Escenario estático torre+persona** (foco actual, sin vacas ni ciclistas): geometría canónica
  validada por el harness (máximo score para torre y persona): **progreso 0.50 del tramo con
  lateral 0**, que con la misión canónica (9 tramos de 162.1 m, 8 m/s) da trigger a 61 m
  (reacción = 45 + 2·v), rejoin en ~0.94 del tramo y 6 detecciones limpias. Los tres encuentros
  del protocolo F2/F3 (torre → persona → torre) van en los **tramos 1, 3 y 5** (un tramo vacío
  entre ellos, ~192 m nominales entre rejoin y siguiente trigger). Protocolos:
  `run_paper_wp1_wp2_tower.py --protocol f1|f2|f3` (F1 = mismos objetos y ruta desplazados 70 m
  laterales: detectables a <80 m, fuera del horizonte de reacción → 0 replans; **ocultar solo a la
  persona no basta**, las torres del corredor dispararían igual). Resultados: F1 201 detecciones
  limpias / 0 replans / 0 fallos; F2 y F3 3 planes, 3 evasiones completadas y 0 fallos cada uno.
  En el gemelo, la escena `porce_static` (Unreal, copia de Ejea) reproduce esa geometría con
  `PORCE_Tower_T1` (tramo 1), `PORCE_Person_P1` (tramo 3) y `PORCE_Tower_T2` (tramo 5) a la misma
  cota, pelotón y torres heredadas ocultas; se genera con `Unreal/Scripts/porce_add_static_person.py`
  (parámetro `MODE = conflict|dormancy`). El humano es el escaneo "Ryan Full Body"
  (`local_data/paper_assets/person_model_ryan/`, FBX generado con `tools/ryan_scan_to_fbx.py`;
  ver `docs/THIRD_PARTY_ASSETS.md`).
- **Runtime ejecutable desde clone limpio**: una sola fuente de configuración en `src/configs/`;
  misión por defecto `missions/ejea_canonical_523m.waypoints`; peso YOLO en `src/weights/`
  (se restaura desde `local_data/`); salidas en `runs/`; ArduPilot obtenido por commit
  `26ac908b7058638796888bddb1a498becce7d3d7` con `tools/bootstrap_ardupilot.ps1`.
  `tools/legacy/` conserva herramientas retiradas que NO forman parte de la reproducción ni
  del release.
- **Instrumentación de revisores ya implementada** (sin cambiar el algoritmo): `plan_ms` y
  `route_points_latlon` en los eventos de ruta, `plan_ms`/`control_loop_dt_ms` en
  `decision_snapshot`, timestamps captura→inferencia→publish y `vision_cycle_ms` en visión,
  `setpoint_sent` por cada consigna GUIDED enviada al autopiloto, y `run_meta.json` por run
  (hash de misión/peso, commits, plataforma, hora UTC). Estado de la campaña real:
  `evidence/field/README.md`.
- **Tests**: 28/28 en local y en CI (`.github/workflows/tests.yml`), incluida regresión del bug
  A03, higiene de rutas, provenance de submission y mapa de failsafe 3→HOLD / 5→REPLAN_LATERAL /
  6→LAND.
- **Evidencia física PF1/PF2/PF3**: los tres vuelos están acreditados con expedientes completos
  (BIN nativo, tlog, brain, config, survey, metadatos) en `evidence/field/`, acta canónica en
  `evidence/field/README.md`. El vídeo de percepción (G6) lo incorpora el operador; mientras
  tanto las figuras de campo permanecen en cola de actualización.

- **Repositorio público**: el historial anterior contiene material interno de trabajo; el
  artefacto de revisores se publicará como rama huérfana `reviewer-release` (sin historial)
  cuando el paper esté cerrado.

## 2. Reproducción rápida

Requisitos: Python 3.12 y las dependencias de `src/configs/requirements.lock.txt`
(ultralytics 8.4.110, flask 3.1.2, pymavlink 2.4.49, opencv 4.11.0, numpy 1.26.4,
matplotlib 3.10.8, pytest; torch CPU es suficiente). Windows solo es necesario para captura
de pantalla; el análisis de logs funciona en cualquier SO.

```
# 1) Tabla del paper (se recomputa desde evidence/zero_trust_runs/)
python analysis/verify_sim_metrics.py
#    esperado (run auditado 20260731_061815): 576.5 s / 1465.4 m / 28.2 s / 29.6 m / 23 replans

# 2) Figuras cuantitativas (bit-exactas a evidence/figures/)
python analysis/make_logged_campaign_figures.py

# 3) Tests
pytest -q tests        # 28/28

# 4) Assets pesados (peso YOLO, imágenes RW, vídeo) para compilar/ejecutar visión
powershell -File tools/restore_external_assets.ps1

# 5) Compilar el manuscrito canónico
cd paper/revision
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex

# 6) SITL (ArduPilot por commit congelado), opcional
powershell -File tools/bootstrap_ardupilot.ps1 -BuildSITL
```

Experimentos: la campaña simulada está en `experiments/sim_static_cow/` (launchers + manifiesto
de runs). La evidencia física se gestionará en `experiments/field_3targets/` cuando el dossier
F1/F2/F3 esté auditado. La antigua campaña SITL multi-torre queda solo como posible soporte
estadístico, nunca como evidencia principal.

### Publicación en Overleaf

El manuscrito canónico `paper/revision/main.tex` se publica en el proyecto Overleaf
`6aa92339ca32e18a56ad4776` (<https://www.overleaf.com/project/6aa92339ca32e18a56ad4776>).
El deploy vive fuera de Git en `local_data/overleaf/deploy/` y se sincroniza con
`SYNC_OVERLEAF.bat` (o `tools/sync_overleaf.ps1 [-Compile]`). Solo se suben los ficheros
gestionados (`Main/correccion.tex`, `references_main.bib`, `Definitions/*`, imágenes);
`Main/main.tex`, `Main/Feedback_xabi.tex` y `Main/no_tocar_references_main.bib` de Overleaf
no se tocan.

## 3. Estructura

- Versionado (ligero): `paper/`, `review/`, `src/`, `missions/`, `experiments/`, `analysis/`,
  `tests/`, `evidence/`, `docs/`, `tools/`, `external_data/`.
- **Local, fuera de Git**: `local_data/` (logs completos, .BIN, peso YOLO, replay, assets
  pesados/privados, documentos archivados) y `runs/` (salidas de ejecución).
- Hashes de lo pesado: `external_data/HEAVY_EXTERNAL_MANIFEST.csv`.
- Herramientas retiradas del flujo actual (Unreal/SPPA/Pipeline B) quedaron fuera de Git;
  no usarlas como evidencia.
- Dependencias externas/compartidas (Unreal, venv, pesos YOLOE, Pipeline B, Overleaf, ArduPilot)
  y el paper hermano dinámico IEEE (`../PORCE_DINAMICO/`): ver `docs/EXTERNAL_DEPENDENCIES.md`.

## 4. Trabajo pendiente (orden recomendado)

1. Auditar el dossier PF1/PF2/PF3 contra `evidence/field/README.md` en cuanto se
   suba (qué logs existen, si `plan_ms`/timestamps están presentes en el runtime volado, ground
   truth y hashes). No escribir cifras antes.
2. Commit de paper (sin tocar vuelo real): portar al canónico las correcciones ya verificadas
   (failsafe 3/5/6, rasterización `ceil(Rs/Δ)` + `force_include`), limpiar reviewnotes no-real,
   bib/EASA/duplicados y simplificar la Fig. 1.
3. Ingesta y análisis de vuelo: tablas por vuelo y por encuentro, true vs perceived clearance,
   figura cenital media+envolvente (ver `review/response_to_reviewers.md`, estados
   `PENDING_EVIDENCE`).
4. Reescritura de Results/abstract/conclusiones con las cifras auditadas (solo entonces).
5. Experimentación de revisores: benchmark A*/RRT*/DWA offline, sensibilidad
   Rs/D_base/k_v/velocidad, precisión YOLO + geoposicionamiento, runtime en hardware embarcado.
6. Revisión de análisis histórico: `verify_sim_metrics` por manifiesto explícito, separar
   cohortes 23/45 m, una única fórmula de `evasion_s`, misiones históricas verificadas.
7. Cierre: `review/response_to_reviewers.md` definitivo, rama huérfana `reviewer-release`, tag
   inmutable y DOI Zenodo tras revisar licencias/privacidad.

## 5. Reglas de trabajo

- No cambiar el algoritmo para que "encaje" con el texto: si hay divergencia, corregir la
  descripción.
- Los vuelos físicos permanecen sin acreditar; cualquier dossier se audita contra el contrato
  antes de escribir cifras y la sección de campo permanece congelada hasta entonces.
- Todo parche de código con test; toda cifra nueva con trazabilidad en
  `local_data/planning/20260921/review/CLAIM_PROVENANCE.csv`.
- Nada pesado/sensible en Git: `local_data/` + fila en el manifiesto de hashes.
- No publicar material sensible (WhatsApp, tokens, personas identificables).

## 6. Licencias y terceros

- **Código PORCE** (`src/`, análisis, tests): del proyecto Deep-AeroTwin/PORCE. Licencia por
  decidir (propuesta MIT/Apache-2.0) antes del release/Zenodo.
- **Plantilla LaTeX MDPI** (`paper/*/Definitions/`): distribuible para envíos a MDPI; no
  reutilizar para otra editorial sin revisar condiciones.
- **ArduPilot**: GPLv3, commit `26ac908b7058638796888bddb1a498becce7d3d7`; no se redistribuye
  la fuente en este repo (`local_data/ardupilot`).
- **Unreal Engine 5.7.x/5.8** y **Cesium for Unreal + Google 3D Tiles**: EULA/términos propios;
  no redistribuir binarios, assets ni cachés de tiles.
- **Ultralytics YOLO** (AGPL-3.0): dependencia pip; revisar la política del peso entrenado antes
  de publicarlo.
- **Fondo satelital Google** en figuras de campo: revisar permisos o sustituir por ortofoto
  PNOA (IGN, uso público) antes del release.
