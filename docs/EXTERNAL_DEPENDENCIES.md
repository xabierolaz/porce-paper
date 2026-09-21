# Dependencias externas y material compartido

Este repo (`porce-paper/`) es la única fuente del paper PORCE estático (MDPI *Electronics*)
y de su runtime. El material **compartido con otros papers o con el twin Unreal** vive fuera y
se referencia aquí; no se duplica dentro del repo.

| Recurso | Ruta (fuera de este repo, o dentro pero fuera de Git) | Para qué lo usa PORCE | Notas |
|---|---|---|---|
| Proyecto Unreal + Cesium | `..\Unreal\` (`AirTraffic.uproject`, UE 5.8) y `..\Unreal\Scripts\` (`cow_evasion_cinematic.py`, `render_cow_evasion_v2.py`, `build_peloton_evasion_v*.py`, ...) | Render de los escenarios de evasión (vaca/pelotón) | Compartido con SPPA/VRIH; no redistribuible (EULA UE/Cesium) |
| Entorno Python de los lanzadores | `..\venv\` | Ejecutar runtime/tools en Windows | Regenerable desde `src/configs/requirements.lock.txt` |
| Pesos YOLOE / MobileCLIP de experimentos | `..\yoloe-11m-seg.pt`, `..\yoloe-11s-seg.pt`, `..\yoloe-26s-seg.pt`, `..\mobileclip2_b.ts`, `..\mobileclip_blt.ts` | Experimentos de detección abierta (compartidos con SPPA/VRIH) | **No** es el peso canónico PORCE; ese está en `local_data/yolo/weights/` |
| Vídeo/figure de torres (Pipeline B) | `..\video_final_yolo_towers.mp4`, `..\tower_dets_video_final.json`, `..\yolo_towers_video_final.py`, `..\annotate_video_final_yolo.py`, `..\cap_f*.png`, `..\build_paper_figure.py`, `..\build_side_by_side.py`, `..\unreal_recording_manual.mp4`, `..\media\side_by_side_twin.*` | Torres eléctricas (escenario compartido estático/twin) | Gestionado por `..\papers\pipeline_b_telemetry\` |
| Capturas intermedias de sesiones Unreal | `..\renders\`, `..\rec_flight\`, `..\rec_flight_final\`, `..\rec_test\`, `..\pipeline\` | Salidas de render/grabación | Regenerables; no son evidencia del paper |
| Documentación MCP de Unreal | `..\KIMI_CLAUDE_UNREAL_MCP_GUIDE.md`, `..\README.md` | Cómo controlar el editor UE desde un agente | Infra compartida |
| Overleaf (proyecto vivo) | https://www.overleaf.com/project/6aa92339ca32e18a56ad4776 | Compilación/entrega del manuscrito | Deploy local (fuera de Git): `local_data/overleaf/deploy/`; sync: `SYNC_OVERLEAF.bat` |
| ArduPilot (SITL) | `local_data/ardupilot/` (commit `26ac908b...`) | Reproducir la campaña SITL | GPLv3; no se redistribuye en Git |
| Paper hermano dinámico (IEEE TII) | `..\PORCE_DINAMICO\` | Manuscrito de obstáculo móvil (pelotón) | Fuera de este repo por alcance (solo paper estático aquí) |

Regla: si algo es **exclusivo de PORCE** y el paper/runtime lo usa, vive dentro de este repo
(Git si es texto ligero; `local_data/` si es pesado/inmutable). Si es **compartido**, se queda
fuera y se referencia en esta tabla.
