# Recursos de terceros (assets)

Los assets de terceros usados por PORCE se documentan aquí con su licencia y fuente.
No redistribuir fuera de los términos indicados.

## Modelo de persona estática (simulación / gemelo)

| Campo | Valor |
|---|---|
| Fichero | `local_data/paper_assets/person_model_ryan/` (fuera de Git): `Ryan Full Body.obj` + `.mtl` + `Body2_2.png` (+ `SHA256.txt`) |
| Uso | Actor estático de persona (clase `person`) en el escenario `porce_static`, sobre el corredor de vuelo |
| Procedencia | Escaneo de cuerpo completo "Ryan Full Body" aportado por el propietario del proyecto (2026-09-20) |
| Licencia | No redistribuir; uso interno del proyecto y figuras con consentimiento de la persona escaneada |
| Importado a UE | `/Game/PORCE/Person/Ryan` (StaticMesh + material) — ver `Unreal/Scripts/porce_add_static_person.py` |

Sustituye al placeholder anterior "Cesium Man" (CC-BY 4.0, © Cesium), retirado del repo el 2026-09-20.
