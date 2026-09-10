from telegram import Update
from telegram.ext import ContextTypes
from config import get_now_wib
from storage import load_tugas_data, save_tugas_data
from utils import (
    is_valid_deadline,
    is_valid_time,
    normalize_time,
    parse_deadline_input,
    cleanup_expired_tasks,
)

async def tambahtugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahtugas [Nama Tugas] | [DD-MM-YYYY] | [Matkul] | [Jam (opsional)]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda '|' (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahtugas [Nama Tugas] | [Deadline DD-MM-YYYY] | [Mata Kuliah (opsional)] | [Jam HH:MM (opsional)]`\n\n"
            "💡 **Contoh:**\n"
            "• *Dengan Jam:* `/tambahtugas Laporan Modul 2 | 20-08-2026 | Keamanan Jaringan | 23:59`\n"
            "• *Atau Jam Digabung:* `/tambahtugas Laporan Modul 2 | 20-08-2026 23:59 | Keamanan Jaringan`\n"
            "• *Tanpa Jam:* `/tambahtugas Tugas Resume | 20-08-2026 | Sistem Operasi`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return 

    bagian = [b.strip() for b in input_teks.split("|")]
    nama_tugas = bagian[0]
    deadline_raw = bagian[1] if len(bagian) > 1 else "-"
    matkul = bagian[2] if len(bagian) > 2 and bagian[2] else "Umum"
    jam_raw = bagian[3] if len(bagian) > 3 else "-"

    parsed_date, parsed_time = parse_deadline_input(deadline_raw)

    if not parsed_date:
        pesan = (
            "⚠️ **Format deadline tidak valid.**\n\n"
            "Kamu bisa gunakan format angka atau nama bulan:\n"
            "• `12-09-2026`\n"
            "• `12 september 2026`\n"
            "• `2026 september 12`\n"
            "• `september 12 2026`\n"
            "(Bisa ditambahkan jam opsional di bagian akhir, contoh: `23:59`)"            
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    deadline_str = parsed_date

    if jam_raw == "-" and parsed_time:
        jam_raw = parsed_time
    
    if is_valid_time(jam_raw):
        jam_str = normalize_time(jam_raw)
    else:
        jam_str = "-"

    tugas_list = cleanup_expired_tasks()
    next_id = max([t.get("id", 0) for t in tugas_list], default=0) + 1

    tugas_baru = {
        "id": next_id,
        "nama_tugas": nama_tugas,
        "deadline": deadline_str,
        "jam": jam_str,
        "matkul": matkul,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    tugas_list.append(tugas_baru)
    if save_tugas_data(tugas_list):
        jam_display = f"{jam_str} WIB" if jam_str != "-" else "Tidak ditentukan"
        pesan = (
            f"✅ **Tugas Berhasil Ditambahkan!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📝 **Tugas:** {nama_tugas}\n"
            f"📕 **Matkul:** {matkul}\n"
            f"📅 **Deadline:** {deadline_str}\n"
            f"⏰ **Waktu / Jam:** {jam_display}\n\n"
            "Ketik `/listtugas` untuk melihat semua tugas yang belum selesai."
        )
    else:
        pesan = "❌ Gagal menyimpan tugas ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def listtugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /listtugas"""
    tugas_list = cleanup_expired_tasks()
    if not tugas_list:
        await update.message.reply_text("🎉 **Tidak ada tugas aktif!** Kamu bebas tugas untuk saat ini.", parse_mode="Markdown")
        return

    pesan = "📋 **DAFTAR TUGAS KULIAH AKTIF**:\n"
    for t in tugas_list:
        jam_str = t.get("jam", "-")
        jam_info = f" (Pukul {jam_str} WIB)" if jam_str and jam_str != "-" else " (Jam tidak ditentukan)"
        pesan += f"\n🆔 **ID:** `#{t.get('id')}`\n"
        pesan += f"📝 **Tugas:** {t.get('nama_tugas', '-')}\n"
        pesan += f"📕 **Matkul:** {t.get('matkul', '-')}\n"
        pesan += f"⏰ **Deadline:** {t.get('deadline', '-')}{jam_info}\n"
        pesan += f"----------------------------"

    pesan += "\n\n💡 *Gunakan `/selesai [ID]` jika tugas sudah dikerjakan.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def selesai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /selesai [ID]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID tugas yang ingin diselesaikan.\nContoh: `/selesai 1`", parse_mode="Markdown")
        return

    target_id_str = context.args[0].replace("#", "")
    if not target_id_str.isdigit():
        await update.message.reply_text("⚠️ ID tugas harus berupa angka. Contoh: `/selesai 1`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    tugas_list = cleanup_expired_tasks()

    tugas_ditemukan = None
    sisa_tugas = []
    for t in tugas_list:
        if t.get("id") == target_id:
            tugas_ditemukan = t
        else:
            sisa_tugas.append(t)

    if not tugas_ditemukan:
        await update.message.reply_text(f"❌ Tugas dengan ID `#{target_id}` tidak ditemukan.", parse_mode="Markdown")
        return

    save_tugas_data(sisa_tugas)
    pesan = (
        f"🎉 **Selamat! Tugas Berhasil Diselesaikan:**\n\n"
        f"📝 *{tugas_ditemukan.get('nama_tugas')}* ({tugas_ditemukan.get('matkul')})\n\n"
        "Tugas telah dihapus dari daftar tugas aktif."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")
