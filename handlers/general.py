from telegram import Update
from telegram.ext import ContextTypes
from storage import register_subscriber
from utils import generate_daily_briefing

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
    if update.effective_chat:
        register_subscriber(update.effective_chat.id)
    user_name = update.effective_user.first_name if update.effective_user else "Mahasiswa"
    pesan = (
        f"Halo {user_name}! 👋\n\n"
        "Saya adalah **Bot Pengingat Jadwal & Tugas Kuliah**.\n\n"
        "Gunakan perintah berikut:\n"
        "• `/jadwal` - Cek jadwal kuliah hari ini\n"
        "• `/jadwal [hari/semua]` - Cek jadwal hari tertentu atau sepekan\n"
        "• `/rutinitas` - Lihat daftar rutinitas harian\n"
        "• `/help` - Panduan lengkap perintah"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /help"""
    pesan = (
        "📌 **Panduan Perintah Bot**:\n\n"
        "📅 **Jadwal & Rutinitas**:\n"
        "• `/jadwal` - Cek jadwal kuliah hari ini\n"
        "• `/jadwal senin` - Jadwal hari Senin (bisa diganti hari lain)\n"
        "• `/jadwal semua` - Jadwal kuliah lengkap sepekan\n"
        "• `/rutinitas` - Daftar rutinitas hari ini\n"
        "• `/rutinitas semua` - Seluruh daftar rutinitas lengkap\n"
        "• `/tambahrutinitas [Hari] | [Jam] | [Keterangan]` - Tambah rutinitas baru\n"
        "• `/hapusrutinitas [ID]` - Hapus rutinitas\n"
        "• `/beresrutinitas [ID]` - Coret rutinitas selesai hari ini\n\n"
        "📝 **Manajemen Tugas:**\n"
        "• `/tambahtugas [Nama] | [Deadline] | [Matkul] | [Jam (opsional)]` - Catat tugas baru\n"
        "• `/listtugas` - Daftar tugas aktif\n"
        "• `/selesai [ID]` - Tandai tugas selesai / hapus\n\n"
        "📌 **To-Do Spontan (Non-Kuliah):**\n"
        "• `/todo [Kegiatan] | [Hari]` - Catat to-do dengan target hari (bisa tanpa hari)\n"
        "• `/listtodo` - Daftar to-do aktif (bisa `/listtodo [hari]`)\n"
        "• `/berestodo [ID 1] [ID 2]` - Coret to-do yang selesai\n\n"  
        "📅 **Agenda & Event Khusus:**\n"
        "• `/tambahagenda [Acara] | [Tanggal/Hari] | [Jam/Lokasi]` - Catat agenda baru (format tanggal fleksibel)\n"
        "• `/agenda` - Daftar agenda mendatang\n"
        "• `/hapusagenda [ID 1] [ID 2]` - Hapus agenda yang selesai\n\n"      
        "⏰ **Pengingat Otomatis:**\n"
        "• `/cekpengingat` - Cek ringkasan briefing hari ini sekarang\n"
        "• *Bot juga otomatis mengirim briefing setiap jam 05:00 pagi!*\n\n"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def cekpengingat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /cekpengingat (melihat pesan briefing secara instan)"""
    pesan = generate_daily_briefing()
    await update.message.reply_text(pesan, parse_mode="Markdown")
