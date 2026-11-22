from __future__ import annotations

import calendar
import hashlib
import html
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import requests

from .config import Config

log = logging.getLogger(__name__)

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_SUMBER = re.compile(r"^\s*Sumber\s*:\s*[^—–|]{0,100}", re.IGNORECASE)
_POST = re.compile(r"\s*The post\b.*?appeared first on\b.*$", re.IGNORECASE)


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    summary: str
    source: str
    published: datetime | None

    @property
    def uid(self) -> str:
        basis = normalisasi(self.title) or self.link
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def bersihkan(teks: str, batas: int = 400) -> str:
    teks = html.unescape(_TAG.sub(" ", teks or ""))
    teks = _SPACE.sub(" ", teks).strip()
    teks = _SUMBER.sub("", teks)
    teks = _POST.sub("", teks)
    return _SPACE.sub(" ", teks).strip()[:batas]


def normalisasi(teks: str) -> str:
    teks = unicodedata.normalize("NFKC", teks or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", teks).strip()


def _waktu(entry) -> datetime | None:
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if not st:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def _sumber(feed_url: str, entry) -> str:
    meta = entry.get("source", {})
    judul = meta.get("title") if hasattr(meta, "get") else None
    if judul:
        return bersihkan(judul, 60)
    return feed_url.split("/")[2] if "//" in feed_url else feed_url


def ambil_satu(url: str, cfg: Config) -> list[Article]:
    hasil: list[Article] = []
    try:
        resp = requests.get(
            url,
            timeout=cfg.request_timeout,
            headers={"User-Agent": "NewsDigestBot/1.0 (RSS reader)"},
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Gagal mengambil %s: %s", url, exc)
        return hasil

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        log.warning("Feed tidak terbaca %s: %s", url, parsed.bozo_exception)
        return hasil

    batas = datetime.now(timezone.utc) - timedelta(hours=cfg.lookback_hours)
    for entry in parsed.entries:
        judul = bersihkan(entry.get("title", ""), 300)
        tautan = urljoin(url, entry.get("link", "") or "")
        if not judul or not tautan:
            continue

        waktu = _waktu(entry)
        if waktu is not None and waktu < batas:
            continue

        hasil.append(
            Article(
                title=judul,
                link=tautan,
                summary=bersihkan(entry.get("summary", entry.get("description", "")), 500),
                source=_sumber(url, entry),
                published=waktu,
            )
        )

    log.info("%s -> %d artikel", url, len(hasil))
    return hasil


def gabungkan(kumpulan: list[list[Article]], batas: int) -> list[Article]:
    """Gabungkan beberapa sumber RSS/scraper lalu hilangkan duplikat."""
    hasil: list[Article] = []
    tautan_dipakai: set[str] = set()
    judul_dipakai: set[str] = set()

    for artikel in (item for grup in kumpulan for item in grup):
        kunci = normalisasi(artikel.title)
        if artikel.link in tautan_dipakai or (kunci and kunci in judul_dipakai):
            continue
        tautan_dipakai.add(artikel.link)
        judul_dipakai.add(kunci)
        hasil.append(artikel)

    hasil.sort(
        key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return hasil[:batas]


def ambil_semua(cfg: Config) -> list[Article]:
    return gabungkan([ambil_satu(url, cfg) for url in cfg.feeds], cfg.max_articles)
