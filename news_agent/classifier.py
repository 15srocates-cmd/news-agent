from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass

import requests

from .config import Config
from .fetcher import Article

log = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

SYSTEM_PROMPT = """Kamu adalah editor berita berbahasa Indonesia yang fokus pada Kota Sukabumi, Jawa Barat. Tugasmu hanya mengklasifikasikan satu artikel.

Kategori yang diperbolehkan: {kategori}.

Artikel sudah disaring agar relevan dengan Sukabumi. Jika menyebut Kabupaten Sukabumi dan Kota Sukabumi, bedakan keduanya dengan tepat di ringkasan.

Balas HANYA dengan objek JSON valid, tanpa penjelasan, tanpa markdown, dengan tiga kunci:
- "kategori": salah satu dari daftar kategori di atas (persis sama ejaannya)
- "ringkasan": satu kalimat ringkas dalam bahasa Indonesia, maksimal 20 kata
- "penting": angka bulat 1 sampai 10, seberapa penting berita ini bagi pembaca umum

Jangan mengarang fakta. Gunakan hanya judul dan ringkasan yang diberikan."""

USER_PROMPT = """Judul: {judul}
Ringkasan: {ringkasan}
Sumber: {sumber}
"""


@dataclass(frozen=True)
class Label:
    kategori: str
    ringkasan: str
    penting: int


class Klasifikator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.url = f"{cfg.ollama_host}/api/chat"
        self.session = requests.Session()

    def sehat(self) -> bool:
        try:
            return self.session.get(f"{self.cfg.ollama_host}/api/tags", timeout=5).ok
        except requests.RequestException:
            return False

    def klasifikasikan(self, artikel: Article) -> Label:
        payload = {
            "model": self.cfg.ollama_model,
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(kategori=", ".join(self.cfg.kategori)),
                },
                {
                    "role": "user",
                    "content": USER_PROMPT.format(
                        judul=artikel.title,
                        ringkasan=artikel.summary or "(tidak ada ringkasan)",
                        sumber=artikel.source,
                    ),
                },
            ],
            "options": {"temperature": 0.1, "num_predict": 160},
        }

        for percobaan in range(1, 3):
            try:
                resp = self.session.post(self.url, json=payload, timeout=self.cfg.ollama_timeout)
                resp.raise_for_status()
                return self._urai(resp.json()["message"]["content"], artikel)
            except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
                log.warning(
                    "Klasifikasi gagal (percobaan %d) untuk %s: %s",
                    percobaan,
                    artikel.title[:60],
                    exc,
                )
                if percobaan < 2:
                    time.sleep(2 * percobaan)

        log.warning("Memakai label fallback untuk: %s", artikel.title[:60])
        return Label(
            kategori="Lainnya",
            ringkasan=(artikel.summary or artikel.title)[:160],
            penting=5,
        )

    def _urai(self, isi: str, artikel: Article) -> Label:
        bersih = _FENCE.sub("", (isi or "").strip()).strip()
        data = json.loads(bersih)
        if not isinstance(data, dict):
            raise ValueError("bukan objek JSON")

        kategori = str(data.get("kategori", "Lainnya")).strip()
        if kategori not in self.cfg.kategori:
            kategori = "Lainnya"

        try:
            penting = int(data.get("penting", 5))
        except (TypeError, ValueError):
            penting = 5
        penting = max(1, min(10, penting))

        ringkasan = str(data.get("ringkasan", "")).strip() or (artikel.summary or artikel.title)
        return Label(kategori=kategori, ringkasan=ringkasan[:200], penting=penting)
