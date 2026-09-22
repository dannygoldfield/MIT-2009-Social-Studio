"""Read-only audit; never modifies an HPR file or repository."""

import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for baseline in json.loads((root / "docs/hpr-read-only-baseline.json").read_text()):
    repo = Path.home() / "Projects" / baseline["repository"]
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).split(b"\0")
    h = hashlib.sha256()
    for rel in sorted(n for n in tracked if n):
        path = repo / rel.decode()
        h.update(rel)
        if path.is_file():
            h.update(hashlib.sha256(path.read_bytes()).digest())
    assert head == baseline["commit"], f"{repo.name}: commit changed"
    assert h.hexdigest() == baseline["tracked_content_sha256"], f"{repo.name}: content changed"
    assert not subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"], text=True
    ).strip(), f"{repo.name}: working copy changed"
    print(f"{repo.name}: unchanged")
