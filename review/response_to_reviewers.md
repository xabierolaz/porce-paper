# Response to Reviewers — PORCE (major revision)

Internal working document. One entry per reviewer comment (52 total), generated from
`local_data/planning/20260921/review/feedback_52_verbatim.txt` (verbatim text preserved). Statuses are honest by
construction:

| Status | Meaning |
|---|---|
| `RESOLVED` | Verified in the repository (not merely acknowledged in text). |
| `IN_PROGRESS` | Concrete change or experiment planned/partially applied; tracked in `README.md`. |
| `PENDING_EVIDENCE` | Requires the audited physical-flight dossier (acta `evidence/field/README.md`, run folders `evidence/field/PF1_20260919_0914`, `PF2_20260919_1016`, `PF3_20260920_1009`); no number will be written before that audit. |
| `SCOPE_REDUCED` | The unsupported part is removed from scope and declared (e.g., dynamic obstacles → Future Work). |
| `OPEN_LIMITATION` | Declared as a limitation; not experimentally closed. |

The three physical flights (PF1/PF2/PF3) have already been flown and their dossier is
consolidated and audited: see the acta `evidence/field/README.md` and the run folders
`evidence/field/PF1_20260919_0914`, `evidence/field/PF2_20260919_1016` and
`evidence/field/PF3_20260920_1009` (BIN + tlog + brain + config + survey + metadata, each with a
`metadata/hashes.sha256` manifest). The manuscript's field section remains frozen for now, and no
real-flight claim is added or removed until the operator-supplied perception video/overlay (dossier
gate G6) closes `DATA-003`.

| ID | Severity | Reviewer comment (verbatim) | Planned change / response | Status |
|---|---|---|---|---|
| R2-G0 | S0 BLOQUEANTE | El manuscrito parece más un informe de implementación que una contribución académica; falta innovación teórica/científica clara. | P1.12/P1.19: ablación system-level (PORCE vs A* siempre activo) y contribución científica separada de YOLO/A*. | `IN_PROGRESS` |
| R3-1 | S0 BLOQUEANTE | Aclarar y reforzar la innovación y contribución teórica frente a YOLO, A* y técnicas maduras. | P1.12/P1.19: la novedad se formula como política/control contract y se demuestra con benchmark/ablación. | `IN_PROGRESS` |
| R4-B2 | S0 BLOQUEANTE | La novedad de PORCE no está clara; explicar qué es técnicamente nuevo frente a métodos existentes de evitación local. | P1.12/P1.20: tabla de diferencias técnicas y evidencia comparativa homogénea. | `IN_PROGRESS` |
| R4-D6 | S0 BLOQUEANTE | Explicar claramente cómo difiere la estrategia de replanning local de PORCE de métodos existentes. | P1.12/P1.22: descripción explícita de trigger, bounded goal, reattachment y failsafe frente a replanners existentes. | `IN_PROGRESS` |
| R4-D8 | S0 BLOQUEANTE | Comparar PORCE con ESLS y EAODA, que ya tratan obstáculos estáticos/dinámicos en 3D y retorno a la ruta; comparación directa si es posible. | P1.12/P1.20: EAOA y ESLS identificadas y comparadas bibliográficamente (EAOA: Ghaddar & Merei, Future Internet 12(2):29, 2020); benchmark solo bajo protocolo común. | `IN_PROGRESS` |
| R3-2 | S0 BLOQUEANTE | Rs=12 m y la distancia/reacción dinámica son empíricas; realizar análisis de sensibilidad de parámetros. | P1.11: sensibilidad Rs/D_base/k_v/velocidad con OAT sobre la misma misión (pendiente de ejecutar). | `IN_PROGRESS` |
| R4-D10 | S0 BLOQUEANTE | Justificar cuantitativamente los 12 m y relacionar rango de detección, FOV/sensores, velocidad/reacción, maniobra/frenado, reaction range e inflación del obstáculo. | P1.10/P1.11: justificación cuantitativa a partir de error de geoposicionamiento, latencia y respuesta de maniobra; el 12 m es margen operacional, no SORA. | `IN_PROGRESS` |
| R4-E5 | S0 BLOQUEANTE | Evaluar precisión de detección YOLO y precisión de geoposicionamiento monocular, especialmente porque esos errores justifican el radio de 12 m. | P1.10: precision/recall/mAP por clase + error horizontal p50/p95 contra ground truth (requiere datos de percepción; parte del dossier PF1/PF2/PF3, `evidence/field/`). | `PENDING_EVIDENCE` |
| R3-3 | S0 BLOQUEANTE | Añadir comparación cuantitativa con métodos típicos (A*, RRT*, DWA, etc.) usando longitud de ruta, tiempo de cómputo y distancia segura. | P1.12: benchmark planner-level A*/RRT*/DWA con mismo mapa, start/goal, inflación y criterio de colisión. | `IN_PROGRESS` |
| R1-5 | S0 BLOQUEANTE | La evaluación usa criterios insuficientes; añadir más métricas y comparar los resultados con otros estudios/métodos. | P1.9/P1.12/P1.24: más métricas (tabla por condición, true/perceived clearance, runtime) y comparación controlada. | `IN_PROGRESS` |
| R2-8 | S0 BLOQUEANTE | Los vuelos reales son demasiado cualitativos; añadir clearance mínimo, tiempo de planificación y desviación de trayectoria. | P0.2/P1.9: se cuantifica la campaña física con clearance ground-truth, tiempo de planificación y desviación, a partir del dossier PF1/PF2/PF3 auditado (`evidence/field/README.md`). La sección de campo permanece congelada y aún no incorpora esas métricas agregadas. | `PENDING_EVIDENCE` |
| R4-E1 | S0 BLOQUEANTE | En validación real: describir mejor escenarios, número de ensayos y métricas de rendimiento. | P1.7/P1.8: escenario topografiado, protocolo fijo y número exacto de vuelos PF1/PF2/PF3 con todos los intentos. | `PENDING_EVIDENCE` |
| R4-E3 | S0 BLOQUEANTE | Reportar número exacto de simulaciones y vuelos, y número de casos exitosos y fallidos. | P1.8: denominador completo de simulaciones (20, 8 válidas) y de vuelos físicos (3 vuelos, encuentros como sub-unidad); ningún fallo se elimina. | `PENDING_EVIDENCE` |
| R4-E6 | S0 BLOQUEANTE | Añadir consumo de energía, tiempo de finalización, longitud de ruta y tasa de éxito/completitud; mostrar landing path o declarar que no se planifica/optimiza. | P1.9: duración, longitud, completitud y landing declarado fuera de PORCE; energía solo si la señal BAT es válida. | `PENDING_EVIDENCE` |
| R4-E7 | S0 BLOQUEANTE | Las afirmaciones de robustez y repetibilidad necesitan evidencia cuantitativa adicional. | P1.7/P1.9: repetibilidad cuantificada con PF2/PF3 y envolvente media de rutas, sin exagerar la potencia estadística. | `PENDING_EVIDENCE` |
| R3-4 | S0 BLOQUEANTE | Evaluar robustez ante errores de percepción: errores de detección y desviaciones de posicionamiento. | P1.10: perturbaciones controladas estáticas de percepción/posicionamiento (sin objetivos móviles). | `IN_PROGRESS` |
| R3-5 | S0 BLOQUEANTE | Ampliar validación más allá de obstáculos estáticos: escenarios complejos, múltiples obstáculos y objetivos dinámicos. | P0.3/P1.7: se añade multi-obstáculo estático (tres encuentros) y los obstáculos dinámicos pasan explícitamente a Future Work; parte dinámica del comentario reducida de alcance. | `SCOPE_REDUCED` |
| R3-6 | S0 BLOQUEANTE | Demostrar rendimiento en tiempo real: runtime, hardware, frecuencia de control y uso de recursos. | P1.3/P1.13: instrumentación añadida (plan_ms, timestamps, control_loop_dt_ms); falta la campaña de medida en hardware embarcado. | `IN_PROGRESS` |
| R4-D9 | S0 BLOQUEANTE | Aclarar o retirar el claim “Regulatory Compliant”: no se implementa SORA completo y el radio de 12 m es heurístico; no hacer un claim más amplio de lo soportado. | P1.17/P1.21: 'Regulation-Aware', sin claim de cumplimiento formal ni de SORA completo; el límite se declara en Limitations. | `IN_PROGRESS` |
| R1-1 | S1 ALTA | El resumen debe incluir resultados numéricos concretos de rendimiento. | P1.18: el abstract se rellenará solo con cifras regeneradas de la campaña final. | `IN_PROGRESS` |
| R4-A4 | S1 ALTA | Añadir al abstract estadísticas clave: tasa de éxito, mejora, comparación con métodos existentes y diferencia simulación-real. | P1.18: estadísticas clave y comparación; la diferencia sim-real se responderá con el dossier PF1/PF2/PF3 ya auditado (`evidence/field/`). | `PENDING_EVIDENCE` |
| R1-2 | S1 ALTA | En la introducción: explicitar mejor el gap de literatura, dar contribuciones concretas con valores numéricos y añadir el outline del artículo al final. | P1.19: gap explícito, contribuciones medibles y outline (v4 ya incluye outline). | `IN_PROGRESS` |
| R4-B1 | S1 ALTA | Reescribir las contribuciones indicando claramente qué se propone, qué se desarrolla y qué se valida experimentalmente. | P1.19: separar propuesta/desarrollo/validación en las contribuciones. | `IN_PROGRESS` |
| R1-4 | S1 ALTA | La conclusión debe resumir lo realizado con cifras, discutir restricciones del sistema y presentar future work. | P1.26: conclusiones con cifras verificadas, restricciones y future work. | `IN_PROGRESS` |
| R2-7 | S1 ALTA | La conclusión es demasiado general; añadir resultados cuantitativos y limitaciones. | P1.26: conclusión cuantitativa y no general. | `IN_PROGRESS` |
| R3-8 | S1 ALTA | Ampliar limitaciones y future work: barreras dinámicas, modelado de riesgo complejo, optimización multiobjetivo y entornos inciertos. | P1.25–P1.26: dinámicos, 3D, incertidumbre, riesgo complejo y multiobjetivo como future work. | `IN_PROGRESS` |
| R4-F1 | S1 ALTA | Crear una sección dedicada de Limitations con supuestos y límites: entorno, tipos de obstáculo, landing, alcance regulatorio, etc. | P1.25: sección Limitations dedicada (ya existe en v4; se completa). | `IN_PROGRESS` |
| R2-9 | S1 ALTA | Justificar el uso de A* 2D, explicar por qué se ignora la altitud y delimitar el alcance del método. | P1.22/P1.25: justificación de A* 2D y altitud fija; alcance delimitado. | `IN_PROGRESS` |
| R4-D3 | S1 ALTA | Aclarar por qué no se considera evitación 3D y si el UAV mantiene altitud fija durante la maniobra. | P1.22/P1.25: sin evitación 3D; altitud fija declarada. | `IN_PROGRESS` |
| R4-D7 | S1 ALTA | Justificar usar el waypoint actual como objetivo y explicar la ventaja frente a otros métodos waypoint-based de evitación local. | P1.20/P1.22: el waypoint activo como referencia local, con las excepciones reales del código (goal proyectado, sustitución, force-advance). | `IN_PROGRESS` |
| R4-E4 | S1 ALTA | Aclarar la novedad de los obstáculos a nivel del suelo frente a trabajos previos de obstacle avoidance durante landing; comparar si hay datos. | P1.20: distinguir replanning local durante inspección frente a emergency landing; sin claim numérico fuera de protocolo. | `IN_PROGRESS` |
| R4-C3 | S1 ALTA | Añadir tabla comparativa con tipo de obstáculo, 2D/3D, detección, planner local, landing, simulación, real y métricas. | P1.20: tabla comparativa con tipo de obstáculo, 2D/3D, detección, planner, landing, sim/real y métricas. | `IN_PROGRESS` |
| R4-E2 | S1 ALTA | Mostrar en resultados reales evidencia visual de detección (obstáculo/bounding boxes) equivalente a la mostrada en simulación. | P0.2/P1.10: evidencia visual real (frames con bboxes) procedente del dossier PF1/PF2/PF3 auditado (`evidence/field/`; vídeo/overlay del operador pendiente, gate G6). | `PENDING_EVIDENCE` |
| R4-A3 | S1 ALTA | Destacar con más claridad en el abstract que existe validación en escenario real. | P0.2/P1.18: el abstract solo destacará validación física cuando exista evidencia auditada; hasta entonces queda como está, sin retirar el material de vuelo. | `PENDING_EVIDENCE` |
| R3-7 | S1 ALTA | Incluir/discutir planificación basada en reinforcement learning (ej. Q-learning recomendado) y contrastar aprendizaje vs métodos deterministas. | P1.20: discusión bibliográfica de Q-learning/RL y trade-off frente a determinismo; sin benchmark experimental. | `IN_PROGRESS` |
| R1-3 | S2 MEDIA | Reestructurar el paper: Related Work alineado con el outline, después Technical Background y finalmente Methodology en forma limpia. | P1.20–P1.24: Related Work unificada → Background → Method → Setup → Results. | `IN_PROGRESS` |
| R4-C1 | S2 MEDIA | Combinar las antiguas secciones 1.1, 1.2 y 1.3 en una única sección Related Works. | Related Work unificada en v4 (verificado). | `RESOLVED` |
| R4-C2 | S2 MEDIA | Reorganizar el estado del arte en párrafos más cortos y enfocados: 2D, 3D, landing y otros enfoques. | P1.20: párrafos cortos por familia (2D/local, 3D/landing, inspección, riesgo/regulación, learning). | `IN_PROGRESS` |
| R4-D1 | S2 MEDIA | Cambiar “Materials & Methods” por un título más específico, por ejemplo “PORCE Method”. | 'PORCE Method' aplicado en v4 (verificado). | `RESOLVED` |
| R4-D4 | S2 MEDIA | Mejorar Figure 1: fuente mayor, menos frases y flowchart simple del workflow. | P1.22: Figure 1 simplificada y vectorial (pendiente de regenerar). | `IN_PROGRESS` |
| R4-D5 | S2 MEDIA | Presentar pseudocódigo académico estándar con pasos, entradas, decisiones y salidas, no código de implementación. | P1.22: pseudocódigo académico (v4 ya convertido; se valora entorno Algorithm). | `IN_PROGRESS` |
| R4-D11 | S2 MEDIA | Separar configuración/implementación experimental de la metodología en una sección Experimental Setup. | Experimental Setup separado en v4 (verificado). | `RESOLVED` |
| R4-F2 | S2 MEDIA | Revisar la organización global y separar con claridad contribuciones, métodos existentes, implementación y resultados experimentales. | P1.20–P1.24: separación clara de literatura, método, setup y resultados. | `IN_PROGRESS` |
| R4-A2 | S2 MEDIA | Indicar el nombre completo/específico del simulador Unreal utilizado. | P1.23: nombre y versión exactos de Unreal/Cesium usados en los runs finales. | `IN_PROGRESS` |
| R2-6 | S2 MEDIA | Aumentar fuentes y anotaciones demasiado pequeñas en algunas figuras. | §9: fuentes legibles al tamaño final en figuras. | `IN_PROGRESS` |
| R2-5 | S2 MEDIA | Eliminar referencias provisionales tipo “Figure X” y revisar todas las referencias cruzadas. | P1.27: 0 referencias provisionales y revisión de referencias cruzadas. | `IN_PROGRESS` |
| R4-A1 | S3 EDITORIAL | Evitar abreviaturas como UAV en el abstract; usar el término completo. | Término completo en el abstract (v4 usa 'unmanned-aircraft'). | `RESOLVED` |
| R2-1 | S3 EDITORIAL | Eliminar abreviaturas de la lista que no se usan o son poco relevantes (DOAJ, LD, MDPI, TLA). | Abreviaturas podadas en v4 (verificado). | `RESOLVED` |
| R2-2 | S3 EDITORIAL | Normalizar formato de unidades (p. ej. 45 meter, 12 m, 61 m). | P1.27: unidades SI consistentes. | `IN_PROGRESS` |
| R2-3 | S3 EDITORIAL | Realizar una revisión completa del inglés: gramática, artículos, singular/plural y redacción. | P1.27: revisión completa de inglés antes del envío. | `IN_PROGRESS` |
| R2-4 | S3 EDITORIAL | Unificar capitalización y terminología: Flight Plan, Mission, autopilot, etc. | P1.27: terminología y capitalización únicas (mission, flight plan, UAS, autopilot). | `IN_PROGRESS` |
| R4-D2 | S3 EDITORIAL | Revisar errores tipográficos y gramaticales en Materials & Methods, incluidas las líneas indicadas por el revisor. | P1.27: corrección tipográfica/gramatical final. | `IN_PROGRESS` |

Total: 52 comments.
