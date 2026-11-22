from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_FEEDS: tuple[str, ...] = (
    "https://www.antaranews.com/rss/terkini.xml",
    "https://rss.tempo.co/",
    "https://www.sindonews.com/feed",
    "https://feeds.bbci.co.uk/indonesia/news/rss.xml",
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


@dataclass(frozen=True)
class Config:
    feeds: tuple[str, ...] = field(default_factory=_feeds_env)
    kategori: tuple[str, ...] = KATEGORI

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
