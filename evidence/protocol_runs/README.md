# Protocolos de simulación F1/F2/F3 (Brain real, MAVLink mock)

Metadatos de los runs del harness estático experiments/paper_wp1_wp2_tower/run_paper_wp1_wp2_tower.py --protocol f1|f2|f3:

- Geometría: misión canónica Ejea (9 tramos de 162.1 m), 8 m/s.
- Objetos: torre (tramo 1), persona (tramo 3), torre (tramo 5), progreso 0.50, lateral 0 (F2/F3) o 70 m (F1).
- Resultados (2026-09-20): F1 201 detecciones limpias / 0 replans / 0 fallos; F2 y F3 3 evasiones completadas y 0 fallos.
- Los logs completos (`events.jsonl`, `trajectory.csv`, `setpoint_sent`) viven en
  `runs/paper_wp1_wp2_tower/` (fuera de Git).
- La campaña física usa otra geometría (ver `evidence/field/README.md`).
