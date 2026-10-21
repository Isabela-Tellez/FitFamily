"""Deterministic evidence identifiers (Persona 1 - Juan).

The ids are persisted, so they must not depend on Python's salted ``hash()``.
"""

import os
import subprocess
import sys
from pathlib import Path

from src.tools.evidence_ids import stable_evidence_id


def test_evidence_id_is_reproducible_and_distinguishes_each_part():
    first = stable_evidence_id("source_renta_media", "renta media", "https://a.example")
    assert first == stable_evidence_id(
        "source_renta_media", "renta media", "https://a.example"
    )
    assert first != stable_evidence_id(
        "source_renta_media", "renta media", "https://b.example"
    )
    assert first != stable_evidence_id(
        "source_renta_media", "otra variable", "https://a.example"
    )


def test_evidence_id_does_not_confuse_part_boundaries():
    assert stable_evidence_id("p", "a", "b") != stable_evidence_id("p", "a\x1fb")


def test_evidence_id_is_stable_across_python_hash_seeds():
    """A new process with another PYTHONHASHSEED returns the same id."""
    repo = Path(__file__).resolve().parents[1]
    code = (
        "from src.tools.evidence_ids import stable_evidence_id;"
        "print(stable_evidence_id('ev', 'https://gym.example'))"
    )
    outputs = []
    for seed in ("1", "2"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
        outputs.append(completed.stdout.strip())
    assert outputs[0] == outputs[1] == stable_evidence_id("ev", "https://gym.example")
