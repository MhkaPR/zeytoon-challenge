import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _run(out_dir: Path, db: Path):
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    env["DATABASE_URL"] = f"sqlite:///{db}"
    subprocess.run(
        [
            sys.executable,
            "experiments/recommendation/replay.py",
            "--users",
            "1",
            "--max-steps",
            "3",
            "--top-n",
            "5",
            "--no-plots",
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
    )


def test_replay_output_is_byte_identical(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first, tmp_path / "a.sqlite3")
    _run(second, tmp_path / "b.sqlite3")

    a = (first / "replay.jsonl").read_bytes()
    b = (second / "replay.jsonl").read_bytes()
    assert a == b


def test_replay_rows_use_stable_node_ordinals(tmp_path):
    out = tmp_path / "out"
    _run(out, tmp_path / "c.sqlite3")
    text = (out / "replay.jsonl").read_text(encoding="utf-8")
    assert "node_index" in text
    assert "node_id" not in text
