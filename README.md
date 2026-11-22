# Agen Berita Harian (RSS → Ollama → Telegram)

Agen otomatis yang tiap hari mengambil berita RSS berbahasa Indonesia, **memfilternya agar fokus di Kota Sukabumi**, mengkategorikannya dengan **model lokal gratis** (Ollama), lalu mengirim ringkasan ke Telegram. Dijalankan gratis lewat **GitHub Actions**.

## Catatan penting: Ollama vs GitHub Actions

Ollama berjalan di komputer lokal, sementara GitHub Actions berjalan di cloud. Keduanya tetap bisa dipakai bersama dengan cara:

- Ollama **di-install langsung di runner** GitHub Actions (CPU saja, tidak butuh GPU).
- Model (`qwen2.5:3b-instruct`, 1,9 GB) **disimpan di GitHub Actions Cache**, jadi tidak diunduh ulang setiap hari.
- Karena berjalan di CPU, satu artikel butuh beberapa detik. Untuk 40 artikel, totalnya biasanya **5–15 menit**, masih jauh di bawah batas 6 jam runner.

Alternatif kalau nanti ingin lebih cepat: ganti `OLLAMA_MODEL` ke `qwen2.5:0.5b-instruct` (398 MB, lebih cepat tapi kualitasnya lebih rendah), atau pindahkan klasifikasi ke mesin lokal/VPS yang sudah punya Ollama.

## Struktur

```text
news-agent/
├── .github/workflows/daily-news.yml   # penjadwal + instalasi Ollama
├── main.py                            # orkestrasi utama
├── requirements.txt
├── .env.example
└── news_agent/
    ├── config.py                      # semua konfigurasi via environment variable
    ├── fetcher.py                     # ambil + bersihkan + dedup RSS
    ├── scraper.py                     # ambil artikel dari halaman HTML biasa
    ├── classifier.py                  # klasifikasi via Ollama API
    ├── digest.py                      # susun pesan Telegram
    ├── wilayah.py                     # filter & prioritas Kota Sukabumi
    ├── store.py                       # simpan daftar artikel yang sudah dikirim
    └── telegram.py                    # kirim pesan (dengan retry)
```

## Cara pakai

### 1. Buat bot Telegram

1. Chat [@BotFather](https://t.me/BotFather), kirim `/newbot`, ikuti instruksi. Simpan **token**.
2. Dapatkan chat ID:
   - Chat [@userinfobot](https://t.me/userinfobot), lalu salin angka `Id` (untuk chat pribadi), **atau**
   - Tambahkan bot ke grup, kirim pesan ke grup, lalu buka `https://api.telegram.org/bot<TOKEN>/getUpdates` dan salin `chat.id` (biasanya diawali `-100` untuk grup/supergroup).

### 2. Upload ke GitHub

```powershell
cd "D:\OneDrive\Documents\Default Project\news-agent"
git init
git add .
git commit -m "Initial news agent"
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

> Pastikan folder `.github` ikut ter-commit (bagian dari `git add .`).

### 3. Tambahkan 2 Secrets

Di repo GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Nama | Nilai |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token dari BotFather |
| `TELEGRAM_CHAT_ID` | chat ID dari langkah 1 |

### 4. Uji coba

**Actions → Daily Indonesian News Digest → Run workflow**. Pantau lognya. Kalau berhasil, pesan ringkasan masuk ke Telegram.

### 5. Jadwal otomatis

Workflow sudah dijadwalkan tiap hari pukul **00:00 UTC = 07:00 WIB**. Bisa diubah di `daily-news.yml` bagian `cron`.

> Catatan: GitHub kadang menunda scheduled workflow beberapa menit saat jam sibuk. Ini normal.

## Konfigurasi

Semua lewat environment variable di `daily-news.yml` (bagian `env:`) atau file `.env` untuk lokal.

| Variable | Default | Fungsi |
|---|---|---|
| `RSS_FEEDS` | Radar Sukabumi, Media Sukabumi, SukabumiSatu, SukabumiHariIni, Antara Jabar, Antara, Tempo | Daftar RSS, dipisah koma |
| `HTML_PAGES` | `https://www.sukabumiupdate.com/` | **Alamat website HTML biasa**, dipisah koma. Artikel di-scrape dari halaman ini |
| `HTML_MAX_LINKS` | `12` | Maksimal artikel yang diambil per halaman HTML |
| `WILAYAH_MODE` | `wajib` | `wajib` = harus menyebut Sukabumi/kecamatan; `kota` = lebih ketat; `opsional` = tanpa filter |
| `WILAYAH_KEYWORDS` | Sukabumi + 7 kecamatan | Kata kunci untuk mode `wajib` |
| `WILAYAH_PRIORITAS` | Kota Sukabumi, Pemkot, 7 kecamatan | Kata kunci yang menaikkan skor penting +2 |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | Model lokal yang dipakai |
| `LOOKBACK_HOURS` | `24` | Hanya artikel dalam N jam terakhir |
| `MAX_ARTICLES` | `40` | Maksimal artikel diproses per hari |
| `TOP_PER_CATEGORY` | `3` | Berita teratas per kategori yang dikirim |
| `OLLAMA_TIMEOUT` | `120` | Batas waktu per artikel (detik) |
| `REQUEST_TIMEOUT` | `15` | Batas waktu request RSS (detik) |
| `STATE_FILE` | `state/seen.json` | File penanda artikel yang sudah dikirim |

Kategori bawaan: Politik, Ekonomi, Teknologi, Olahraga, Hukum, Sosial, Kesehatan, Pendidikan, Lainnya. Bisa diubah di `news_agent/config.py` (`KATEGORI` dan `EMOJI_KATEGORI`).

## Cara kerja singkat

1. Ambil semua RSS **dan halaman HTML** (`HTML_PAGES`) → buang artikel lebih tua dari 24 jam → hilangkan duplikat (URL + judul).
2. **Filter wilayah** (`news_agent/wilayah.py`): hanya artikel yang menyebut Sukabumi atau salah satu dari 7 kecamatan Kota Sukabumi (Baros, Cibeureum, Cikole, Citamiang, Gunungpuyuh, Lembursitu, Warudoyong). Filter ini dilakukan **sebelum** pembatasan `MAX_ARTICLES`, supaya berita nasional tidak mendesak berita Sukabumi keluar.
3. Bandingkan dengan `state/seen.json` → hanya artikel baru (maks. `MAX_ARTICLES`) yang diproses.
4. Tiap artikel dikirim ke Ollama dengan prompt JSON: `kategori`, `ringkasan`, `penting` (1–10). Berita yang spesifik menyebut **Kota** Sukabumi/Pemkot/kecamatan mendapat **bonus +2** agar muncul lebih atas.
5. Kelompokkan per kategori, urutkan berdasarkan skor penting, ambil top 3.
6. Kirim ke Telegram dalam beberapa pesan (maks. ~3500 karakter per pesan).
7. Simpan daftar artikel ke state **hanya setelah pengiriman berhasil** — jadi kalau Telegram gagal, besoknya dicoba lagi tanpa duplikat.

## Jalankan di lokal (opsional)

Install [Ollama](https://ollama.com/download), lalu:

```powershell
ollama pull qwen2.5:3b-instruct
ollama serve
```

Di terminal lain:

```powershell
cd "D:\OneDrive\Documents\Default Project\news-agent"
pip install -r requirements.txt
copy .env.example .env
# isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env
$env:TELEGRAM_BOT_TOKEN="..."; $env:TELEGRAM_CHAT_ID="..."
python main.py
```

## Troubleshooting

| Masalah | Penanganan |
|---|---|
| Log: `Ollama tidak dapat diakses` | Cek step "Jalankan Ollama" di Actions; lihat `/tmp/ollama.log`. |
| `ollama pull` gagal | Cache model korup → hapus cache `ollama-...` di **Actions → Caches**, lalu jalankan ulang. |
| Telegram `401 Unauthorized` | Token salah. Buat ulang via BotFather. |
| Telegram `Chat not found` | Chat ID salah, atau bot belum pernah di-chat / belum ditambahkan ke grup. |
| Pesan terpotong/aneka | `parse_mode=HTML`; judul sudah di-escape otomatis. Jangan menaruh tag HTML di feed. |
| Berita terlalu banyak | Turunkan `MAX_ARTICLES` atau `TOP_PER_CATEGORY`. |
| Ingin lebih cepat | Ganti model ke `qwen2.5:0.5b-instruct`. |

## Batasan gratis GitHub Actions

- Repo privat: 2000 menit/bulan; publik: unlimited.
- Cache: 10 GB per repo (model 1,9 GB + state kecil → aman).
- Runner: 2 CPU, 7 GB RAM → cukup untuk model 3B.
