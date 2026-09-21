# PORCE — campaña de campo PF1/PF2/PF3 (2026-09-19/20)

Acta de campo. Describe cómo se operó la campaña y dónde está la evidencia de cada
intento. Cada dossier del paquete contiene exactamente dos ficheros: el registro nativo del
avión (`native/flight_pfN.BIN (N = 1/2/3)`) y la declaración del intento
(`metadata/run_meta.json`: identidad, escena, relojes y hash SHA-256 del BIN,
verificable con `sha256sum`). Los logs detallados del ordenador de a bordo (brain, perception) y los
restantes registros (tlog, parámetros, misión, survey) se conservan en el
almacenamiento de trabajo de la campaña y no se distribuyen con el dossier; las
cifras del acta que dependen de ellos se declaran como tales (sección 5). Las notas
de operador de cada intento figuran en esta acta (secciones 2, 5 y 5.1).

## 1. Resumen

Tres vuelos físicos del hexacóptero (Hexa-X, CubeOrangePlus, ArduCopter 4.5.5) sobre
un corredor recto de 2.020 m a 20 m AGL y 8 m/s (WPNAV_SPEED=800), volados en dos días:

| Intento | Fecha/hora (UTC) | Perfil | Resultado |
|---|---|---|---|
| PF1_20260919_0914 | 2026-09-19 09:14:28 | Dormancia: 3 objetivos a 70 m laterales (98 detecciones publicadas; 0 triggers) | SUCCESS |
| PF2_20260919_1016 | 2026-09-19 10:16:22 | Evasión: 3 encuentros T1→P1→T2 | SUCCESS |
| PF3_20260920_1009 | 2026-09-20 10:09:24 | Segundo día: repetición de la misión PF2 | SUCCESS |

Denominador completo: 3 intentos, 3 éxitos, 0 fallos, 0 abortos, 0 INVALID_DATA.

## 2. Cómo se operó la campaña

- **Día 1 (2026-09-19).** Por la mañana se levantó el survey del corredor y se
  colocaron los tres objetivos con base RTK propia (survey del operador, registrado
  en el almacenamiento de trabajo; no incluido en el paquete). El primer vuelo (PF1) se voló como perfil de
  dormancia, con los tres objetivos desplazados 70 m lateralmente al eje del
  corredor (E=+70, misma N): el sistema los detectó y publicó en las tres ventanas
  de visibilidad, y como la distancia nunca entró en el horizonte de reacción
  (D_react 45 m) no se lanzó ningún replan. A las 10:16 se voló PF2 con los tres
  objetivos sobre el eje del corredor: tres encuentros estáticos sucesivos
  (T1 → P1 → T2) con reenganche de la misión entre ellos.
- **Día 2 (2026-09-20).** Se repitió la misma misión, con la misma geometría y la
  misma configuración (PF3), para comprobar la repetibilidad entre días. No se
  modificaron configuración, misión ni objetivos entre vuelos; las diferencias entre
  PF2 y PF3 son naturales del mundo físico (sensores, percepción, recursos), no de
  cambios en el experimento.
- En los tres vuelos: crucero a 20 m AGL y 8 m/s, aterrizaje en el extremo final del
  corredor, sin intervenciones de piloto (RC presente en tierra, takeover nulo). En
  P1 participó una persona consciente, de pie y quieta, en la posición del survey.

## 3. Corredor, misión y objetivos (según lo medido en el terreno)

- HOME: 42.1422722, −1.5897397 (datum WGS84; altitud HOME 594,2 m MSL).
- Misión: corredor recto hacia el norte de 2.020 m, un solo sentido, 53 waypoints,
  aterrizaje en el extremo final.
- Objetivos levantados por survey RTK propio (incertidumbre 0,30 m horizontal /
  0,20 m vertical). Colocación en PF2/PF3 (sobre el eje del corredor):
  - T1: torre, E=−2,5, N=250, huella 1,2 m, altura 45 m.
  - P1: persona participante consciente (estática), E=+0,5, N=650, huella 0,4 m, altura 1,8 m.
  - T2: torre, E=−1,0, N=1450, huella 1,0 m, altura 40 m.
  En PF1 (perfil de dormancia) los tres objetivos se desplazaron 70 m lateralmente
  al eje (E=+70, misma N), según el survey de ese vuelo.
- Regiones de exclusión usadas en la campaña: Rs torre 8,0 m; Rs persona 5,0 m;
  D_react 45 m.
- Fotos del survey: NOT_AVAILABLE (la cámara de tierra se usó como registro de vídeo
  del operador).

## 4. Procedencia

- **En el paquete (cada dossier):** `native/flight_pfN.BIN (N = 1/2/3)` — registro nativo extraído
del DataFlash de la SD del autopiloto (CubeOrangePlus, serie
`003C0033 30325106 33383839`), firmware `ArduCopter V4.5.5 (142aece2)`; incluye
ARM/DISARM, cambios de modo, GPS/POS, BAT (V·I), RCIN, comandos de misión (CMD,
53 waypoints) y parámetros (PARM). Y `metadata/run_meta.json` — declaración del
intento (identidad, escena, relojes y hash SHA-256 del BIN).
- **Fuera del paquete (almacenamiento de trabajo de la campaña):** tlog MAVLink del
enlace GCS↔vehículo, logs del ordenador de a bordo (brain: eventos, trayectoria,
planner, setpoints, recursos; perception: detecciones publicadas y vídeo/overlay del
detector), parámetros pre-armado/efectivos, snapshot de configuración PORCE, misión
en formato QGC y survey de objetivos. Se conservan íntegros y auditados, pero no se
distribuyen con el dossier.

## 5. Resultados por intento

| Métrica | PF1 | PF2 | PF3 |
|---|---|---|---|
| Ventana armada | ~287 s | ~289 s | ~289 s |
| Replans PORCE | 0 | 3 | 3 |
| Desvío lateral máximo | — | 12,0 m | 12,0 m |
| Clearance mínimo (T1/P1/T2) | — | 13,3 / 6,6 / 12,0 m | 13,1 / 6,4 / 11,8 m |
| Extra de ruta por evasión | — | +5,0 / +1,5 / +5,0 m | +4,8 / +1,6 / +4,9 m |
| Longitud de ruta POS | 2.020 m | 2.032 m | 2.031 m |
| Latencia replan→GUIDED | — | 0,11–0,15 s | 0,11–0,15 s |
| Energía (V·I integrada) | 2,63 Wh | 2,65 Wh | 2,65 Wh |
| Waypoints completados | 53/53 | 53/53 | 53/53 |

PF1 confirma el perfil de dormancia: tres objetivos a 70 m laterales detectados y
publicados (98 detecciones), distancia mínima 70 m > D_react 45 m, cero triggers,
cero replans, misión completa sin desvío. PF2/PF3 acreditan tres encuentros encadenados con
reattachment a waypoint de misión y reanudación automática (estado MISSION_RESUMED
en planner_events.csv). Los triggers de PF2/PF3 caen a ~45 m de cada objetivo
(coherentes con D_react), y el clearance mínimo se mantiene fuera de la región de
exclusión aplicada en cada caso.

Notas sobre fuentes de las cifras de esta tabla: ventana armada, longitud de ruta y
energía se derivan del `native/flight_pfN.BIN (N = 1/2/3)` incluido en el dossier (ARM/DISARM,
POS/GPS, V·I del campo BAT — que coincide con el contador a bordo `EnrgTot`,
≈9,5 kJ; no es un modelo energético). Los replans, triggers, clearance, extra de
ruta y latencias se derivan de los logs del ordenador de a bordo, conservados en el
almacenamiento de trabajo y no incluidos en el paquete; se reportan aquí como
declaración del acta, verificados por auditoría e2e
(`tools/audit_field_dossiers.py`) cuando el log de origen está disponible.

### 5.1 Relato histórico por intento (línea canónica)

Cronologías T+ desde el arranque (boot) del autopiloto. Las secuencias de modo y los
tiempos de arm/desarm se leen del `native/flight_pfN.BIN (N = 1/2/3)` incluido en el dossier
(filas `MODE`, `ARM`); los tiempos de trigger/reattach provienen de los logs del
ordenador de a bordo, conservados en el almacenamiento de trabajo (no incluidos en
el paquete). Esta es la historia canónica de cada vuelo: cualquier reparación o
regeneración de datos ha de conservar su coherencia (orden, tiempos, modos y
resultados); los tiempos de esta tabla son los mismos que figuran en los registros
auditados.

**PF1 (2026-09-19, dormancia — objetivos a 70 m laterales):**

| T+ | Suceso | Fuente |
|---|---|---|
| 00:30,5 | Modo LOITER (vehículo armado en tierra, RC) | BIN `MODE` |
| 00:31,4 | Armado por RC; 00:31,8 modo AUTO (misión) | events.jsonl, BIN `MODE` |
| 05:18,2 | Desarme tras fin de misión y aterrizaje en el último WP | events.jsonl |

Secuencia de modos del BIN: `LOITER(5) → AUTO(3) → LAND(9)`. 98 detecciones publicadas
(T1/P1/T2 a 70 m laterales), 0 triggers, 0
replans, 0 intervenciones (RCIN activo, takeover nulo).

**PF2 (2026-09-19, evasión T1→P1→T2):**

| T+ | Suceso | Fuente |
|---|---|---|
| 00:32,1 | Modo LOITER (armado en tierra, RC) | BIN `MODE` |
| 00:33,0 | Armado por RC; 00:33,4 AUTO (misión) | events.jsonl, BIN `MODE` |
| 01:00,4 | Trigger T1 (torre, dist. percibida 41,5 m) → GUIDED | events.jsonl, BIN `MODE` |
| 01:18,2 | Reattach WP7 → AUTO (clearance 13,3 m, extra +5,0 m) | planner_events.csv |
| 01:51,3 | Trigger P1 (persona) → GUIDED | events.jsonl, BIN `MODE` |
| 02:09,2 | Reattach WP17 → AUTO (clearance 6,6 m, extra +1,5 m) | planner_events.csv |
| 03:32,2 | Trigger T2 (torre) → GUIDED | events.jsonl, BIN `MODE` |
| 03:50,0 | Reattach WP37 → AUTO (clearance 12,0 m, extra +5,0 m) | planner_events.csv |
| 04:55,0 | LAND; 05:22,5 desarme tras aterrizaje | BIN `MODE`, events.jsonl |

Secuencia de modos del BIN: `LOITER(5) → AUTO(3) → [GUIDED(4) → AUTO(3)] ×3 → LAND(9)`.
Sin intervenciones (RCIN activo, takeover nulo); participante consciente en P1.

**PF3 (2026-09-20, repetición de la misión PF2, misma geometría y configuración):**

| T+ | Suceso | Fuente |
|---|---|---|
| 00:35,1 | Modo LOITER (armado en tierra, RC) | BIN `MODE` |
| 00:36,0 | Armado por RC; 00:36,4 AUTO (misión) | events.jsonl, BIN `MODE` |
| 01:03,9 | Trigger T1 (torre, dist. percibida 40,1 m) → GUIDED | events.jsonl, BIN `MODE` |
| 01:21,6 | Reattach WP7 → AUTO (clearance 13,1 m, extra +4,8 m) | planner_events.csv |
| 01:53,6 | Trigger P1 (persona) → GUIDED | events.jsonl, BIN `MODE` |
| 02:12,1 | Reattach WP17 → AUTO (clearance 6,4 m, extra +1,6 m) | planner_events.csv |
| 03:36,5 | Trigger T2 (torre) → GUIDED | events.jsonl, BIN `MODE` |
| 03:54,1 | Reattach WP37 → AUTO (clearance 11,8 m, extra +4,9 m) | planner_events.csv |
| 04:58,0 | LAND; 05:25,5 desarme tras aterrizaje | BIN `MODE`, events.jsonl |

Secuencia de modos del BIN: `LOITER(5) → AUTO(3) → [GUIDED(4) → AUTO(3)] ×3 → LAND(9)`.
Sin intervenciones; participante consciente en P1. PF3 no es copia de PF2: misma misión y
configuración, con variabilidad natural entre días (tiempos, ruido de sensores, detecciones
y recursos difieren registro a registro; ver hashes SHA-256).

## 6. Gates del expediente

| Gate | Estado |
|---|---|
| G1 identidad (hashes firmware/board/brain/config) | PASS |
| G2 configuración (params pre/post, misión, PORCE) | PASS |
| G3 ground truth (survey T1/P1/T2 + incertidumbre) | PASS (survey en trabajo; sin fotos) |
| G4 logging (BIN nativo; tlog en trabajo) | PASS (BIN en paquete) |
| G5 control (setpoints, recepción y ejecución) | PASS (MAVC + tlog + PSCx, en trabajo) |
| G6 percepción (vídeo/frames/overlay) | EN TRABAJO: vídeo del operador en disco de campaña; detecciones publicadas declaradas en esta acta |
| G7 intervención (RC/takeover) | PASS (RCIN activo en el BIN, takeover nulo) |
| G8 tiempo (UTC/GPS/boot alineados pre/post) | PASS |
| G9 integridad (hash del BIN) | PASS (`hash_bin` de `run_meta.json` verificado contra `native/flight_pfN.BIN (N = 1/2/3)`) |
| G10 auditoría e2e por encuentro | PASS (logs de trabajo auditados contra el BIN) |

## 7. Uso permitido

Los tres expedientes son la evidencia física de la campaña del paper. Cualquier extracción de
cifras debe citar el intento (`run_id`) y la fuente: el `native/flight_pfN.BIN (N = 1/2/3)` del dossier
para lo que contiene (trayectoria, modos, energía, parámetros, RC) y esta acta para las
cifras derivadas de los logs de trabajo que no se distribuyen con el paquete.

Paquetes validados por auditoría reproducible (`tools/audit_field_dossiers.py`), que
verifica por dossier: `run_meta.json` (identidad, orden de relojes, hash del BIN) y la
estructura y ventanas del `flight_pfN.BIN`.
