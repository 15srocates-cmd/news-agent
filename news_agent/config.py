from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_FEEDS: tuple[str, ...] = (
    "https://radarsukabumi.com/feed/",
    "https://mediasukabumi.id/feed/",
    "https://sukabumisatu.com/feed/",
    "https://sukabumihariini.id/feed/",
    "https://jabar.antaranews.com/rss/terkini.xml",
    "https://www.antaranews.com/rss/terkini.xml",
    "https://rss.tempo.co/",
)

DEFAULT_WILAYAH_KEYWORDS: tuple[str, ...] = (
    "Sukabumi",
    "Kota Sukabumi",
    "Pemkot Sukabumi",
    "Wali Kota Sukabumi",
    "DPRD Sukabumi",
    "Polres Sukabumi",
    "Baros",
    "Cibeureum",
    "Cikole",
    "Citamiang",
    "Gunungpuyuh",
    "Lembursitu",
    "Warudoyong",
)

DEFAULT_WILAYAH_PRIORITAS: tuple[str, ...] = (
    "Kota Sukabumi",
    "Pemkot Sukabumi",
    "Wali Kota Sukabumi",
    "DPRD Kota Sukabumi",
    "Polres Sukabumi Kota",
    "Baros",
    "Cibeureum",
    "Cikole",
    "Citamiang",
    "Gunungpuyuh",
    "Lembursitu",
    "Warudoyong",
)

# Penanda kuat Kota Sukabumi (bukan sekadar nama kecamatan yang juga ada di Kabupaten).
DEFAULT_WILAYAH_KOTA: tuple[str, ...] = (
    "Kota Sukabumi",
    "Sukabumi Kota",
    "Pemkot Sukabumi",
    "Wali Kota Sukabumi",
    "DPRD Kota Sukabumi",
    "Polres Sukabumi Kota",
    "Polres Kota Sukabumi",
    "Pemda Kota Sukabumi",
    "Pemkot",
    "Wali Kota",
    "DPRD Kota",
    "Polres Kota",
    "Pemda Kota",
)

# Penanda Kabupaten Sukabumi, dipakai untuk membuang berita kabupaten di mode "kota".
DEFAULT_WILAYAH_KABUPATEN: tuple[str, ...] = (
    "Kabupaten Sukabumi",
    "Pemkab Sukabumi",
    "Bupati Sukabumi",
    "DPRD Kabupaten Sukabumi",
    "Polres Sukabumi",
    "Pemda Kabupaten Sukabumi",
)

KATEGORI: tuple[str, ...] = (
    "Politik",
    "Ekonomi",
    "Teknologi",
    "Olahraga",
    "Hukum",
    "Sosial",
    "Kesehatan",
    "Pendidikan",
    "Lainnya",
)

EMOJI_KATEGORI: dict[str, str] = {
    "Politik": "🏛️",
    "Ekonomi": "💹",
    "Teknologi": "💻",
    "Olahraga": "⚽",
    "Hukum": "⚖️",
    "Sosial": "🤝",
    "Kesehatan": "🩺",
    "Pendidikan": "📚",
    "Lainnya": "📌",
}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _feeds_env() -> tuple[str, ...]:
    raw = os.getenv("RSS_FEEDS", "").strip()
    if not raw:
        return DEFAULT_FEEDS
    return tuple(url.strip() for url in raw.split(",") if url.strip())


def _daftar_env(nama: str, bawaan: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(nama, "").strip()
    if not raw:
        return bawaan
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Config:
    feeds: tuple[str, ...] = field(default_factory=_feeds_env)
    kategori: tuple[str, ...] = KATEGORI

    wilayah_mode: str = field(default_factory=lambda: os.getenv("WILAYAH_MODE", "kota").lower())
    wilayah_keywords: tuple[str, ...] = field(
        default_factory=lambda: _daftar_env("WILAYAH_KEYWORDS", DEFAULT_WILAYAH_KEYWORDS)
    )
    wilayah_prioritas: tuple[str, ...] = field(
        default_factory=lambda: _daftar_env("WILAYAH_PRIORITAS", DEFAULT_WILAYAH_PRIORITAS)
    )
    wilayah_kota: tuple[str, ...] = field(
        default_factory=lambda: _daftar_env("WILAYAH_KOTA", DEFAULT_WILAYAH_KOTA)
    )
    wilayah_kabupaten: tuple[str, ...] = field(
        default_factory=lambda: _daftar_env("WILAYAH_KABUPATEN", DEFAULT_WILAYAH_KABUPATEN)
    )

    telegram_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct"))
    ollama_timeout: int = field(default_factory=lambda: _int_env("OLLAMA_TIMEOUT", 120))

    lookback_hours: int = field(default_factory=lambda: _int_env("LOOKBACK_HOURS", 24))
    max_articles: int = field(default_factory=lambda: _int_env("MAX_ARTICLES", 40))
    top_per_category: int = field(default_factory=lambda: _int_env("TOP_PER_CATEGORY", 3))

    # Halaman HTML biasa (bukan RSS) yang ingin di-scrape artikelnya.
    html_pages: tuple[str, ...] = field(default_factory=lambda: _daftar_env("HTML_PAGES", ()))
    html_max_links: int = field(default_factory=lambda: _int_env("HTML_MAX_LINKS", 12))

    request_timeout: int = field(default_factory=lambda: _int_env("REQUEST_TIMEOUT", 15))
    state_file: str = field(default_factory=lambda: os.getenv("STATE_FILE", "state/seen.json"))

    def validate(self) -> None:
        kosong = []
        if not self.telegram_token:
            kosong.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            kosong.append("TELEGRAM_CHAT_ID")
        if not self.feeds:
            kosong.append("RSS_FEEDS")
        if kosong:
            raise RuntimeError("Environment variable belum diisi: " + ", ".join(kosong))
        if self.wilayah_mode not in {"wajib", "kota", "opsional"}:
            raise RuntimeError("WILAYAH_MODE harus salah satu dari: wajib, kota, opsional")
