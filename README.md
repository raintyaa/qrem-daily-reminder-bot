# 🤖 Qrem - Bot Telegram Pengingat Jadwal, Tugas, & Agenda Kuliah

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Library](https://img.shields.io/badge/library-python--telegram--bot%20v22-green.svg)
![Deployment](https://img.shields.io/badge/deployment-Railway%20Cloud%2024%2F7-brightgreen.svg)
![Status](https://img.shields.io/badge/status-Completed%20%26%20Active-success.svg)

**Qrem** adalah bot Telegram berbasis Python untuk membantu mengelola jadwal kuliah, deadline tugas, to-do spontan, rutinitas harian, dan agenda kegiatan — lengkap dengan sistem pengingat otomatis *real-time* 24/7.

---

## 🌟 Fitur Utama & Sistem Notifikasi Pintar

* ☀️ **Daily Briefing Pagi (Pukul 05:00 WIB)**: Rangkuman otomatis awal hari yang menggabungkan jadwal kuliah hari ini, status deadline tugas, to-do spontan, dan daftar seluruh agenda kegiatan.
* 🎓 **Alarm Kuliah (1 Jam Sebelum Kelas)**: Pengingat *real-time* 1 jam sebelum jam mulai kuliah (lengkap dengan nama matkul, kelas, dan ruang kuliah).
* 📝 **Pengingat Deadline Tugas**:
  * 🚨 **Hari H Deadline (H-6 Jam)**: Alarm mendesak berbunyi tepat 6 jam sebelum jam batas waktu tugas hari H.
  * 📋 **Sebelum Hari H (Setiap 6 Jam)**: Pengingat berkala tugas mendatang pada pukul **06:00, 12:00, dan 18:00 WIB**.
  * 🛡️ **Filter < 6 Jam**: Tugas yang diinput mepet (< 6 jam sebelum deadline) otomatis dikecualikan dari alarm pengingat berulang.
* ⏰ **Rutinitas Kustom & Fitur Coret (`/beresrutinitas`)**: Alarm pengingat kegiatan rutin harian maupun hari spesifik (misal: salat Jumat atau olahraga akhir pekan) dengan dukungan CRUD penuh via chat (`/tambahrutinitas`, `/hapusrutinitas`) dan fitur centang/coret yang **otomatis di-reset setiap pergantian hari (00:00 WIB)**.
* 📅 **Agenda Kegiatan Khusus & Event Tracker**: Pencatatan acara bertanggal khusus (rapat ormawa, kerja kelompok, webinar) dengan pengingat otomatis pada jam 05:00 pagi di Hari H acara.
* 📌 **To-Do Spontan (Non-Kuliah)**: Pencatatan cepat untuk urusan pribadi/spontan (`/todo`, `/listtodo`, `/berestodo`).

---

## 📋 Daftar Perintah Perangkat (Command Reference)

Bot **Qrem** dilengkapi dengan 17 perintah handler interaktif:

| Perintah | Deskripsi |
| :--- | :--- |
| `/start` | Memulai bot & mendaftarkan chat ID untuk notifikasi otomatis |
| `/help` | Menampilkan panduan lengkap seluruh perintah bot |
| `/jadwal` | Menampilkan jadwal kuliah hari ini |
| `/jadwal [hari/semua]` | Menampilkan jadwal kuliah hari tertentu atau sepekan penuh |
| `/rutinitas` | Menampilkan daftar rutinitas hari ini & status selesainya |
| `/rutinitas [hari/semua]` | Menampilkan rutinitas hari tertentu atau seluruh sepekan |
| `/tambahrutinitas [Hari] \| [Jam] \| [Kegiatan]` | Menambah rutinitas kustom baru (setiap hari atau hari spesifik) |
| `/hapusrutinitas [ID]` | Menghapus kegiatan rutinitas berdasarkan nomor ID |
| `/beresrutinitas [ID 1] [ID 2] ...` | Mencoret satu atau beberapa rutinitas selesai sekaligus (reset otomatis 00:00) |
| `/tambahtugas [Nama] \| [Tanggal] \| [Matkul] \| [Jam]` | Menambah tugas kuliah baru (mendukung format angka & teks bulan fleksibel) |
| `/listtugas` | Menampilkan daftar tugas kuliah aktif & hitung mundur deadline |
| `/selesai [ID]` | Menghapus / menyelesaikan tugas kuliah |
| `/todo [Kegiatan] \| [Hari]` | Mencatat to-do baru dengan target hari spesifik/relatif (default hari ini) |
| `/listtodo [hari/semua]` | Menampilkan daftar to-do aktif (bisa filter per hari) |
| `/berestodo [ID 1] [ID 2] ...` | Mencoret satu atau beberapa to-do selesai sekaligus |
| `/tambahagenda [Acara] \| [Tanggal/Hari] \| [Info]` | Menambah agenda kegiatan khusus baru (mendukung teks bulan, angka, & hari fleksibel) |
| `/agenda` | Menampilkan daftar seluruh agenda mendatang |
| `/hapusagenda [ID 1] [ID 2] ...` | Menghapus satu atau beberapa agenda yang telah terlaksana |
| `/cekpengingat` | Menampilkan pesan briefing harian secara instan kapan saja |

---

## 📂 Struktur Proyek

```text
Daily Reminder Bot/
├── .env.example          # Template konfigurasi token bot
├── .gitignore            # Daftar file yang diabaikan oleh Git
├── Procfile              # Konfigurasi worker deployment cloud (Railway)
├── README.md             # Dokumentasi lengkap proyek
├── bot.py                # Entry point utama; mendaftarkan semua handler & menjalankan scheduler
├── config.py             # Zona waktu WIB, konstanta hari, & path file JSON
├── storage.py            # Logika baca/tulis JSON (jadwal, tugas, todo, agenda, subscriber)
├── utils.py              # Fungsi pembantu (validasi jam, format tanggal, daily briefing)
├── scheduler.py          # Background loop (alarm rutinitas, kuliah 1 jam lagi, reminder tugas, briefing pagi)
├── server.py             # Server mini HTTP health-check untuk monitoring cloud
├── handlers/             # Kumpulan handler perintah Telegram terkelompok rapi
│   ├── __init__.py       # Inisialisasi & ekspor seluruh 17 command handler
│   ├── general.py        # /start, /help, /cekpengingat
│   ├── jadwal.py         # /jadwal, /rutinitas, /tambahrutinitas, /hapusrutinitas, /beresrutinitas
│   ├── tugas.py          # /tambahtugas, /listtugas, /selesai
│   ├── todo.py           # /todo, /listtodo, /berestodo
│   └── agenda.py         # /tambahagenda, /agenda, /hapusagenda
├── jadwal.json           # Data jadwal kuliah & rutinitas harian
├── keep_alive.sh         # Script auto-restart utilitas
├── requirements.txt      # Daftar pustaka dependency Python
├── test_bot.py           # Suite pengujian otomatis (10 test suite)
└── Documentation/        # Dokumentasi tangkapan layar pengujian & notifikasi
```

---

## 💻 Cara Memasang & Menjalankan Lokal

### 1. Prasyarat
* Python 3.10 atau versi yang lebih baru.
* Token Bot Telegram dari `@BotFather`.

### 2. Instalasi
```bash
# Clone repositori ini
git clone https://github.com/raintyaa/qrem-daily-reminder-bot.git
cd qrem-daily-reminder-bot

# Buat & aktifkan virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Token
Salin file `.env.example` menjadi `.env`, lalu isi token bot Telegram-mu:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

### 4. Jalankan Pengujian Suite & Bot
```bash
# Jalankan self-check pengujian otomatis
python test_bot.py

# Jalankan bot
python bot.py
```

---

## ☁️ Deployment 24/7 Cloud (Railway)

Bot ini telah ter-deploy dan aktif 24/7 di **Railway Cloud Server**:
* **Procfile**: `worker: python bot.py`
* **Timezone Locked**: Kodingan dilengkapi pengunci zona waktu **WIB (UTC+7)** menggunakan `timezone(timedelta(hours=7))` sehingga notifikasi berbunyi tepat waktu di server cloud global.
* **Environment Variable**: `TELEGRAM_BOT_TOKEN` disimpan secara aman melalui *secret variables* Railway.

---

## 🗓️ Milestone & Roadmap Pengerjaan

* [x] **Hari 1**: Setup project, Git repository, arsitektur dasar, handler `/start` & `/help`.
* [x] **Hari 2**: Sistem Jadwal Kuliah dinamis berbasis `jadwal.json`.
* [x] **Hari 3**: Manajemen Tugas Kuliah (CRUD `tugas.json`) & hitung mundur deadline.
* [x] **Hari 4**: Sistem Pengingat Otomatis (*Auto-Reminder Loop*) & pendaftaran subscriber.
* [x] **Hari 5**: To-Do Spontan (`/todo`, `/listtodo`, `/berestodo`) & alarm rutinitas per jam.
* [x] **Hari 6**: Agenda & Event Tracker (`/tambahagenda`, `/agenda`, `/hapusagenda`).
* [x] **Hari 7**: Standalone Self-Check Test Suite (`test_bot.py`) dengan 15 verifikasi handler.
* [x] **Hari 8**: Smart Real-Time Alarms (Briefing 05:00 WIB, Alarm Kuliah H-1 Jam, Evaluasi Tugas 20:00 WIB, Auto-Reset Rutinitas).
* [x] **Hari 9**: Konfigurasi `Procfile` & Health-Check Server untuk *production deployment*.
* [x] **Hari 10**: Toleransi port server & pengunci zona waktu WIB (UTC+7).
* [x] **Hari 11**: Deployment resmi 24/7 Nonstop di Railway Cloud & Dokumentasi Final.

---

## 👨‍💻 Pengembang

Dikembangkan oleh **raintyaa** ([Muhammad Zaki Rakha Bahy](https://github.com/raintyaa))