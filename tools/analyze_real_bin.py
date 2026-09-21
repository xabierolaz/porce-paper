#!/usr/bin/env python3
"""Analiza un .BIN DataFlash real para extraer su estructura exacta.

Uso: python tools/analyze_real_bin.py [<fichero.bin>]
Por defecto analiza el vuelo real de referencia M_20_1RR (papers/pipeline_b_telemetry).
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "local_data" / "ardupilot" / "Tools" / "logprofile"))
from pymavlink import DFReader  # noqa: E402

REF_DEFAULT = REPO.parent / "papers" / "pipeline_b_telemetry" / "data" / "M_20_1RR_VIDEO" / "2026-07-06 09-43-41.bin"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bin_path", nargs="?", default=str(REF_DEFAULT))
    args = parser.parse_args()
    ref = Path(args.bin_path)
    if not ref.is_file():
        print(f"[ERROR] no existe: {ref}")
        return 2

    print(f"Abriendo BIN: {ref}")
    reader = DFReader.DFReader_binary(str(ref), None)

    print(f"\n=== FMT: {len(reader.formats)} formatos ===")
    for tid in sorted(reader.formats.keys()):
        fmt = reader.formats[tid]
        print(f"  ID={tid:3d} len={fmt.len:4d} name={fmt.name:10s} cols={fmt.columns[:8]}")

    print("\n=== Registros por tipo ===")
    total = 0
    for tid in sorted(reader.id_to_name.keys()):
        name = reader.id_to_name[tid]
        count = len(reader.offsets[tid]) if tid < len(reader.offsets) else 0
        total += count
        if count > 0:
            print(f"  {name:10s}: {count:6d} registros")
    print(f"  TOTAL: {total}")

    fmt_id = reader.name_to_id.get("FMT")
    if fmt_id is not None:
        print("\n=== Primeros 5 FMT records ===")
        for off in reader.offsets[fmt_id][:5]:
            reader.offset = off
            m = reader._parse_next()
            if m:
                print(f"  Type={m.Type} Length={m.Length} Name={m.Name} Format={m.Format} Columns={m.Columns}")

    parm_id = reader.name_to_id.get("PARM")
    if parm_id is not None:
        print("\n=== Primeros 5 PARM ===")
        for off in reader.offsets[parm_id][:5]:
            reader.offset = off
            m = reader._parse_next()
            if m:
                nm = m.Name[:20] if isinstance(m.Name, str) else m.Name
                print(f"  Name={nm} Value={m.Value} Default={m.Default}")

    ver_id = reader.name_to_id.get("VER")
    if ver_id is not None:
        print("\n=== Primeros 3 VER records ===")
        for off in reader.offsets[ver_id][:3]:
            reader.offset = off
            m = reader._parse_next()
            if m:
                print(f"  {m}")

    raw = ref.read_bytes()
    print("\n=== Cabecera raw (32 bytes) ===")
    print(f"  Hex: {raw[:32].hex()}")
    print(f"  ASCII: {raw[:32]}")

    print("\n=== Primeros 2 registros por tipo (20 bytes) ===")
    for name in ("GPS", "ATT", "BARO", "BAT", "RCOU", "MODE", "ARM", "EV", "PARM"):
        tid = reader.name_to_id.get(name)
        if tid is None or tid >= len(reader.offsets):
            continue
        for off in reader.offsets[tid][:2]:
            print(f"  {name}: {raw[off:off + 20].hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
