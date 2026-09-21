import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src", "tools", "experiments", "analysis")
SCAN_SUFFIXES = {".py", ".ps1", ".bat", ".sh", ".env"}
MACHINE_PATH_PATTERNS = (
    re.compile(r"D:\\Deep-AeroTwin", re.IGNORECASE),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"xabier", re.IGNORECASE),
)
LEGACY_PARTS = ("legacy",)


def _iter_reviewer_files():
    for folder in SCAN_DIRS:
        for path in (REPO / folder).rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if any(part in LEGACY_PARTS for part in path.relative_to(REPO).parts):
                continue
            yield path


def test_no_machine_specific_paths_in_reviewer_facing_files():
    offenders = []
    for path in _iter_reviewer_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in MACHINE_PATH_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(REPO)}: {pattern.pattern}")
    assert offenders == []


def test_no_retired_pipeline_layout_paths():
    offenders = []
    for path in _iter_reviewer_files():
        text = path.read_text(encoding="utf-8", errors="replace").replace("\\", "/").lower()
        if "pipeline/logs" in text or "/pipeline/" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


def test_single_config_source():
    assert (REPO / "src" / "configs" / "porce_defaults.env").is_file()
    assert (REPO / "src" / "configs" / "real_twin_defaults.env").is_file()
    assert (REPO / "src" / "configs" / "requirements.txt").is_file()
    assert (REPO / "src" / "configs" / "requirements.lock.txt").is_file()
    for duplicate in (
        "src/porce_defaults.env",
        "src/real_twin_defaults.env",
        "src/requirements.txt",
        "src/requirements.lock.txt",
    ):
        assert not (REPO / duplicate).exists(), f"duplicate config still present: {duplicate}"


def test_default_mission_and_weight_paths_exist():
    import constants

    assert Path(constants.WAYPOINTS_FILE).is_file()
    assert Path(constants.WAYPOINTS_FILE).parent.name == "missions"
    assert Path(constants.VISION_YOLO_MODEL).name == "yolo_unreal_unrealScene_v1_best_e23_2026-02-18.pt"
    assert "src" in Path(constants.VISION_YOLO_MODEL).parts
    assert Path(constants.VISION_DEFAULT_MODEL_PATH) == Path(constants.VISION_YOLO_MODEL)


def test_canonical_manuscript_provenance_matches():
    provenance = REPO / "paper" / "revision" / "MANUSCRIPT_PROVENANCE.json"
    data = json.loads(provenance.read_text(encoding="utf-8"))
    manuscript = REPO / "paper" / "revision" / "main.tex"
    digest = hashlib.sha256(manuscript.read_bytes()).hexdigest().upper()
    assert digest == data["source_sha256"].upper()


def test_submission_manifest_extracted_files_match_hashes():
    manifest_path = REPO / "paper" / "submitted" / "SUBMISSION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked = 0
    for candidate in manifest["submission_candidates"]:
        for entry in candidate["entries"]:
            if not entry.get("extracted"):
                continue
            extracted = REPO / "paper" / "submitted" / candidate["tag"] / entry["path"]
            digest = hashlib.sha256(extracted.read_bytes()).hexdigest()
            assert digest == entry["sha256"], f"hash mismatch: {extracted}"
            checked += 1
    assert checked >= 5
