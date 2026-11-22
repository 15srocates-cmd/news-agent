from __future__ import annotations

import logging
import time

import requests

from .config import Config

log = logging.getLogger(__name__)


class Telegram:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.endpoint = f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage"

    def kirim(self, pesan: str) -> bool:
        payload = {
            "chat_id": self.cfg.telegram_chat_id,
            "text": pesan,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        for percobaan in range(1, 4):
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=30)
                if resp.ok:
                    return True
                log.error("Telegram %s: %s", resp.status_code, resp.text[:300])
            except requests.RequestException as exc:
                log.error("Telegram gagal (percobaan %d): %s", percobaan, exc)
            if percobaan < 3:
                time.sleep(3 * percobaan)
        return False

    def kirim_semua(self, pesan: list[str]) -> bool:
        for i, teks in enumerate(pesan, 1):
            if not self.kirim(teks):
                log.error("Gagal mengirim bagian %d/%d", i, len(pesan))
                return False
            log.info("Terkirim bagian %d/%d", i, len(pesan))
        return True
