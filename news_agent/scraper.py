from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import Config
from .fetcher import Article, bersihkan, sesi_http

log = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))
_HARI = r"(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu)"
_BULAN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "agu": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
}
_TANGGAL = re.compile(
    rf"{_HARI}\s+(\d{{1,2}})\s+([A-Za-z]{{3}})\s+(\d{{4}}),\s*(\d{{2}}):(\d{{2}})\s*WIB",
    re.IGNORECASE,
)
_TANGGAL_URL = re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})/")
_ARTIKEL = re.compile(r"/\d+/")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){3,}", re.IGNORECASE)
_TIDAK_ARTIKEL = re.compile(
    r"/(?:kategori|category|kategori-berita|tag|tags|topik|author|penulis|page|"
    r"about|tentang|contact|kontak|arsip|archive|search|cari|feed|rss|wp-content|"
    r"wp-admin|login|register|sitemap|privacy|terms)(?:/|$)",
    re.IGNORECASE,
)


def _waktu(teks: str) -> datetime | None:
    m = _TANGGAL.search(teks or "")
    if not m:
        return None
    hari, bulan, tahun, jam, menit = m.groups()
    try:
        return datetime(
            int(tahun), _BULAN[bulan.lower()], int(hari), int(jam), int(menit), tzinfo=WIB
        )
    except (KeyError, ValueError):
        return None


def _waktu_url(tautan: str) -> datetime | None:
    m = _TANGGAL_URL.search(tautan)
    if not m:
        return None
    try:
        return datetime(*(int(x) for x in m.groups()), tzinfo=WIB)
    except ValueError:
        return None


def _waktu_meta(nilai: str | None) -> datetime | None:
    if not nilai:
        return None
    try:
        hasil = datetime.fromisoformat(nilai.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return hasil if hasil.tzinfo else hasil.replace(tzinfo=timezone.utc)


def _adalah_artikel(tautan: str) -> bool:
    if _TIDAK_ARTIKEL.search(tautan):
        return False
    if _ARTIKEL.search(tautan):
        return True
    bagian = [b for b in urlparse(tautan).path.split("/") if b]
    if not bagian:
        return False
    return bool(_SLUG.fullmatch(bagian[-1]))


def _sumber(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def _judul_dari(anchor) -> str:
    for tag in anchor.find_all(["h2", "h3", "h4"]):
        teks = bersihkan(tag.get_text(" ", strip=True), 300)
        if len(teks) >= 20:
            return teks
    if anchor.get("title"):
        teks = bersihkan(anchor["title"], 300)
        if len(teks) >= 20:
            return teks
    gambar = anchor.find("img", alt=True)
    if gambar and len(gambar["alt"]) >= 20:
        return bersihkan(gambar["alt"], 300)
    return bersihkan(anchor.get_text(" ", strip=True), 300)


def _detail(url: str, cfg: Config) -> tuple[str, datetime | None]:
    """Ambil ringkasan dan waktu terbit dari halaman artikel."""
    try:
        with sesi_http() as sesi:
            resp = sesi.get(
                url,
                timeout=cfg.request_timeout,
                headers={"User-Agent": "NewsDigestBot/1.0 (HTML article reader)"},
            )
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.select_one("meta[name='description']") or soup.select_one(
            "meta[property='og:description']"
        )
        ringkasan = ""
        if meta and meta.get("content"):
            ringkasan = bersihkan(meta["content"], 500)
        if not ringkasan:
            h1 = soup.find("h1")
            if h1:
                paragraf = h1.find_next("p")
                if paragraf:
                    ringkasan = bersihkan(paragraf.get_text(" ", strip=True), 500)
        terbit = soup.select_one("meta[property='article:published_time']")
        return ringkasan, _waktu_meta(terbit.get("content") if terbit else None)
    except requests.RequestException as exc:
        log.warning("Gagal mengambil detail %s: %s", url, exc)
    return "", None


def ambil_satu_halaman(url: str, cfg: Config) -> list[Article]:
    hasil: list[Article] = []
    try:
        with sesi_http() as sesi:
            resp = sesi.get(
                url,
                timeout=cfg.request_timeout,
                headers={"User-Agent": "NewsDigestBot/1.0 (HTML article reader)"},
            )
            resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Gagal mengambil halaman %s: %s", url, exc)
        return hasil

    soup = BeautifulSoup(resp.text, "html.parser")
    domain = urlparse(url).netloc
    kandidat: dict[str, tuple[str, datetime | None]] = {}
    for anchor in soup.find_all("a", href=True):
        tautan = urljoin(url, anchor["href"])
        if urlparse(tautan).netloc != domain or not _adalah_artikel(tautan):
            continue
        judul = _judul_dari(anchor)
        if len(judul) < 20 or tautan in kandidat:
            continue
        kandidat[tautan] = (
            judul,
            _waktu(anchor.get_text(" ", strip=True)) or _waktu_url(tautan),
        )

    log.info("%s: %d kandidat artikel", url, len(kandidat))
    batas = datetime.now(timezone.utc) - timedelta(hours=cfg.lookback_hours)

    for tautan, (judul, waktu) in list(kandidat.items())[: cfg.html_max_links]:
        ringkasan, terbit = _detail(tautan, cfg)
        waktu = terbit or waktu
        if waktu is not None and waktu.astimezone(timezone.utc) < batas:
            continue
        hasil.append(
            Article(
                title=judul,
                link=tautan,
                summary=ringkasan,
                source=_sumber(url),
                published=waktu,
            )
        )
    return hasil


def ambil_semua_halaman(cfg: Config) -> list[Article]:
    semua: list[Article] = []
    for url in cfg.html_pages:
        semua.extend(ambil_satu_halaman(url, cfg))
    return semua
