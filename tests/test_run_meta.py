import json
from pathlib import Path

from zero_trust_audit import ZeroTrustAudit


def test_write_run_meta_records_hashes_and_extra(tmp_path):
    audit = ZeroTrustAudit(component="brain", root_dir=str(tmp_path / "zero_trust"))
    mission = tmp_path / "mission.waypoints"
    mission.write_text("QGC WPL 110\n", encoding="utf-8")
    model = tmp_path / "model.pt"
    model.write_bytes(b"weights")

    out = audit.write_run_meta(
        mission_file=str(mission),
        model_file=str(model),
        extra={"condition": "C1_1tower"},
    )

    assert out is not None
    data = json.loads(Path(out).read_text(encoding="utf-8"))
    assert data["component"] == "brain"
    assert data["condition"] == "C1_1tower"
    assert len(data["mission_sha256"]) == 64
    assert len(data["model_sha256"]) == 64
    assert set(("porce_commit", "platform", "python_version", "written_utc")) <= set(data)


def test_write_run_meta_disabled_returns_none(tmp_path):
    audit = ZeroTrustAudit(component="brain", root_dir="")
    assert audit.enabled is False
    assert audit.write_run_meta() is None
