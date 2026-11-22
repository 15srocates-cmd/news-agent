from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from .classifier import Label
from .config import Config, EMOJI_KATEGORI
from .fetcher import Article

WIB = ZoneInfo("Asia/Jakarta")
BATAS_PESAN = 3500


@dataclass(frozen=True)
class Item:
    artikel: Article
    label: Label


def potong(teks: str, batas: int = BATAS_PESAN) -> list[str]:
    if len(teks) <= batas:
        return [teks]

    hasil: list[str] = []
    saat_ini: str = ""
    for baris in teks.split("\n"):
        if len(saat_ini) + len(baris) + 1 > batas and saat_ini:
            hasil.append(saat_ini.rstrip())
            saat_ini = ""
        saat_ini += baris + "\n"
    if saat_ini.strip():
        hasil.append(saat_ini.rstrip())
    return hasil


def susun(artikel: list[Article], label: list[Label], cfg: Config) -> list[str]:
    grup: dict[str, list[Item]] = defaultdict(list)
    for a, l in zip(artikel, label):
        grup[l.kategori].append(Item(a, l))

    tanggal = datetime.now(WIB).strftime("%d %b %Y")
    total = sum(len(items) for items in grup.values())
    bagian: list[str] = [
        "📰 <b>Ringkasan Berita Indonesia</b>\n"
        f"🗓️ {tanggal} · ⏱️ 07.00 WIB\n"
        f"📥 {total} artikel baru dari {len(cfg.feeds)} sumber"
    ]

    for kategori in cfg.kategori:
        items = sorted(
            grup.get(kategori, []),
            key=lambda it: (
                -it.label.penting,
                it.artikel.published or datetime.min.replace(tzinfo=WIB),
            ),
        )[: cfg.top_per_category]
        if not items:
            continue

        emoji = EMOJI_KATEGORI.get(kategori, "📌")
        blok = [f"\n{emoji} <b>{escape(kategori.upper())}</b> ({len(items)})"]
        for no, it in enumerate(items, 1):
            jam = (
                it.artikel.published.astimezone(WIB).strftime("%H:%M")
                if it.artikel.published
                else "-"
            )
            blok.append(
                f"\n{no}. <b>{escape(it.artikel.title)}</b>\n"
                f"   ⭐ {it.label.penting}/10 · {escape(it.artikel.source)} · {jam}\n"
                f"   {escape(it.label.ringkasan)}\n"
                f'   <a href="{escape(it.artikel.link, quote=True)}">Baca artikel ↗</a>'
            )
        bagian.append("\n".join(blok))

    # Gabungkan blok yang masih muat agar tidak mengirim banyak pesan kecil.
    digabung: list[str] = []
    for blok in bagian:
        if digabung and len(digabung[-1]) + len(blok) + 1 <= BATAS_PESAN:
            digabung[-1] += "\n" + blok
        else:
            digabung.append(blok)

    pesan: list[str] = []
    for teks in digabung:
        pesan.extend(potong(teks))
    return pesan
