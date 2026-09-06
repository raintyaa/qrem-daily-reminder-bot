import os
import sys
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler

# 1. Modul Konfigurasi
from config import (
    TOKEN,
    PORT,
    WIB,
    HARI_INDONESIA,
    BASE_DIR,
    JADWAL_FILE,
    TUGAS_FILE,
    TODO_FILE,
    AGENDA_FILE,
    RUTINITAS_SELESAI_FILE,
    CONFIG_FILE,
    get_now_wib,
)

# 2. Modul Akses Penyimpanan Data JSON
from storage import (
    load_jadwal_data,
    save_jadwal_data,
    load_tugas_data,
    save_tugas_data,
    load_todo_data,
    save_todo_data,
    load_agenda_data,
    save_agenda_data,
    load_rutinitas_selesai_data,
    save_rutinitas_selesai_data,
    load_subscribers,
    register_subscriber,
)

# 3. Modul Pembantu (Utility & Format)
from utils import (
    is_valid_time,
    normalize_time,
    normalize_rutinitas_item,
    is_valid_deadline,
    get_task_deadline_dt,
    should_remind_task,
    format_jadwal_hari,
    generate_daily_briefing,
)

# 4. Modul Scheduler Pengingat Otomatis
from scheduler import auto_reminder_loop

# 5. Modul Server Health Check
from server import start_health_check_in_background

# 6. Modul Kumpulan Handler Perintah Telegram (17 Handlers)
from handlers import (
    start_command,
    help_command,
    cekpengingat_command,
    jadwal_command,
    rutinitas_command,
    beresrutinitas_command,
    tambahrutinitas_command,
    hapusrutinitas_command,
    tambahtugas_command,
    listtugas_command,
    selesai_command,
    todo_command,
    listtodo_command,
    berestodo_command,
    tambahagenda_command,
    agenda_command,
    hapusagenda_command,
)


async def post_init(application) -> None:
    """Otomatis dijalankan saat bot aktif untuk menyalakan background scheduler task"""
    asyncio.create_task(auto_reminder_loop(application))


def build_app(token: str):
    """Membangun aplikasi bot Telegram dengan seluruh 17 handler terdaftar & scheduler aktif"""
    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Perintah Dasar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cekpengingat", cekpengingat_command))

    # Jadwal Kuliah & Rutinitas
    app.add_handler(CommandHandler("jadwal", jadwal_command))
    app.add_handler(CommandHandler("rutinitas", rutinitas_command))
    app.add_handler(CommandHandler("tambahrutinitas", tambahrutinitas_command))
    app.add_handler(CommandHandler("hapusrutinitas", hapusrutinitas_command))
    app.add_handler(CommandHandler("beresrutinitas", beresrutinitas_command))

    # Tugas Kuliah
    app.add_handler(CommandHandler("tambahtugas", tambahtugas_command))
    app.add_handler(CommandHandler("listtugas", listtugas_command))
    app.add_handler(CommandHandler("selesai", selesai_command))

    # To-Do Spontan (Non-Kuliah)
    app.add_handler(CommandHandler("todo", todo_command))
    app.add_handler(CommandHandler("listtodo", listtodo_command))
    app.add_handler(CommandHandler("berestodo", berestodo_command))

    # Agenda Kegiatan
    app.add_handler(CommandHandler("tambahagenda", tambahagenda_command))
    app.add_handler(CommandHandler("agenda", agenda_command))
    app.add_handler(CommandHandler("hapusagenda", hapusagenda_command))

    return app


def main() -> None:
    """Fungsi utama untuk menjalankan Bot Qrem"""
    if not TOKEN or TOKEN == "your_telegram_bot_token_here":
        print("\n[PERINGATAN] TELEGRAM_BOT_TOKEN belum diisi di file .env!")
        print("Silakan buka file .env dan ganti 'your_telegram_bot_token_here' dengan token dari @BotFather.\n")
        sys.exit(1)

    # Jalankan server mini HTTP di background thread untuk health check monitoring Railway
    start_health_check_in_background(PORT)

    print("Bot Qrem sedang berjalan... Tekan Ctrl+C untuk menghentikan.")
    app = build_app(TOKEN)
    app.run_polling()


if __name__ == "__main__":
    main()
