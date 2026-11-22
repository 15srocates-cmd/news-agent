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


def _ada(teks: str, kata: tuple[str, ...]) -> bool:
    return any(k in teks for k in kata)


def saring(artikel: list[Article], cfg: Config) -> list[Article]:
    """Saring artikel sesuai mode wilayah.

    wajib    : harus menyebut Sukabumi / kecamatan Kota Sukabumi
    kota     : hanya Kota Sukabumi — penanda kuat kota, atau kecamatan yang
               tidak disertai penanda Kabupaten Sukabumi
    opsional : tidak menyaring, hanya memberi bonus prioritas
    """
    if cfg.wilayah_mode == "opsional":
        return artikel

    pasangan = [(a, _teks(a)) for a in artikel]

    if cfg.wilayah_mode == "kota":
        kota = _kata_kunci(cfg.wilayah_kota)
        kecamatan = tuple(k for k in _kata_kunci(cfg.wilayah_prioritas) if k not in kota)
        kabupaten = _kata_kunci(cfg.wilayah_kabupaten)
        # Penanda singkat ("Pemkot", "Wali Kota", ...) hanya dihitung kalau
        # artikelnya memang menyebut Sukabumi.
        hasil = [
            a
            for a, teks in pasangan
            if ("sukabumi" in teks and _ada(teks, kota))
            or (_ada(teks, kecamatan) and not _ada(teks, kabupaten))
        ]
    else:
        kata = _kata_kunci(cfg.wilayah_keywords)
        hasil = [a for a, teks in pasangan if _ada(teks, kata)] if kata else artikel

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
