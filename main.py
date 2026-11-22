from __future__ import annotations

import logging
import sys
from dataclasses import replace

from news_agent import classifier, digest, fetcher, store, wilayah
from news_agent.config import Config
from news_agent.telegram import Telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")


def jalankan(cfg: Config) -> int:
    cfg.validate()
    log.info(
        "Model: %s | feed: %d | jendela: %d jam",
        cfg.ollama_model,
        len(cfg.feeds),
        cfg.lookback_hours,
    )

    artikel = fetcher.ambil_semua(cfg)
    log.info("Total artikel terambil: %d", len(artikel))
    artikel = wilayah.saring(artikel, cfg)
    if not artikel:
        log.info("Tidak ada artikel yang relevan dengan wilayah. Selesai.")
        return 0

    seen = store.muat(cfg.state_file)
    baru = [a for a in artikel if a.uid not in seen]
    log.info("Artikel baru: %d", len(baru))
    if not baru:
        log.info("Semua artikel sudah pernah dikirim. Selesai.")
        return 0

    klasi = classifier.Klasifikator(cfg)
    if not klasi.sehat():
        raise RuntimeError(f"Ollama tidak dapat diakses di {cfg.ollama_host}")

    label = []
    for i, a in enumerate(baru, 1):
        log.info("[%d/%d] %s", i, len(baru), a.title[:70])
        hasil = klasi.klasifikasikan(a)
        tambahan = wilayah.bonus(a, cfg)
        if tambahan:
            hasil = replace(hasil, penting=min(10, hasil.penting + tambahan))
        label.append(hasil)

    pesan = digest.susun(baru, label, cfg)
    log.info("Pesan Telegram: %d bagian", len(pesan))

    if not Telegram(cfg).kirim_semua(pesan):
        log.error("Pengiriman gagal; state tidak disimpan agar bisa dicoba lagi.")
        return 1

    store.simpan(cfg.state_file, seen, [a.uid for a in baru])
    log.info("Selesai. %d artikel disimpan ke state.", len(baru))
    return 0


if __name__ == "__main__":
    sys.exit(jalankan(Config()))
