from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)
BATAS_RIWAYAT = 1000


def muat(path: str) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return set(data.get("seen", [])) if isinstance(data, dict) else set()
    except (OSError, ValueError) as exc:
        log.warning("Gagal membaca state %s: %s", path, exc)
        return set()


def simpan(path: str, seen: set[str], tambahan: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    gabungan = list(dict.fromkeys([*sorted(seen), *tambahan]))[-BATAS_RIWAYAT:]
    try:
        p.write_text(
            json.dumps({"seen": gabungan}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        log.warning("Gagal menyimpan state %s: %s", path, exc)
