from __future__ import annotations

import logging

from .config import Config
from .fetcher import Article, normalisasi

log = logging.getLogger(__name__)


def _kata_kunci(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(k for k in (normalisasi(item) for item in items) if k)


def _teks(artikel: Article) -> str:
    # Sumber sengaja tidak dimasukkan: "Radar Sukabumi" akan membuat semua artikel lolos.
    return normalisasi(f"{artikel.title} {artikel.summary}")


def saring(artikel: list[Article], cfg: Config) -> list[Article]:
    """Saring artikel sesuai mode wilayah.

    wajib    : harus menyebut Sukabumi / kecamatan Kota Sukabumi
    kota     : lebih ketat, harus menyebut Kota Sukabumi / Pemkot / kecamatan
    opsional : tidak menyaring, hanya memberi bonus prioritas
    """
    if cfg.wilayah_mode == "opsional":
        return artikel

    kata = _kata_kunci(
        cfg.wilayah_prioritas if cfg.wilayah_mode == "kota" else cfg.wilayah_keywords
    )
    if not kata:
        return artikel

    hasil = [a for a in artikel if any(k in _teks(a) for k in kata)]
    log.info(
        "Filter wilayah (%s): %d dari %d artikel lolos",
        cfg.wilayah_mode,
        len(hasil),
        len(artikel),
    )
    return hasil


def bonus(artikel: Article, cfg: Config) -> int:
    """Tambah skor penting untuk berita yang spesifik Kota Sukabumi."""
    kata = _kata_kunci(cfg.wilayah_prioritas)
    return 2 if any(k in _teks(artikel) for k in kata) else 0
