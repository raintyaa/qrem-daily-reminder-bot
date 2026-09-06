from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import get_now_wib, HARI_INDONESIA
from storage import load_agenda_data, save_agenda_data
from utils import parse_deadline_input

async def tambahagenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahagenda [Nama Acara] | [Tanggal/Hari] | [Jam/Lokasi]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda `|` (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahagenda [Nama Acara] | [Tanggal / Hari] | [Jam / Lokasi]`\n\n"
            "💡 **Pilihan Tanggal/Hari:**\n"
            "• Tanggal angka: `22-08-2026`\n"
            "• Teks nama bulan: `12 september 2026`, `september 12 2026`\n"
            "• Hari spesifik: `senin`, `jumat`, `minggu`\n"
            "• Hari relatif: `hari ini`, `besok`, `lusa`\n\n"
            "💡 **Contoh:**\n"
            "• `/tambahagenda Rapat Ormawa | 22-08-2026 | 16:00 di Gedung B`\n"
            "• `/tambahagenda Kerja Kelompok IoT | 12 september 2026 | 10:00 di Perpus`\n"
            "• `/tambahagenda Futsal Akbar | jumat | 19:00 di Lapangan Futsal`\n"
            "• `/tambahagenda Evaluasi Bulanan | besok 20:00 | Zoom`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    bagian = [b.strip() for b in input_teks.split("|")]
    nama_acara = bagian[0]
    tanggal_raw = bagian[1] if len(bagian) > 1 else "-"
    keterangan = bagian[2] if len(bagian) > 2 else "Tanpa keterangan"

    parsed_date, parsed_time = parse_deadline_input(tanggal_raw)

    if not parsed_date:
        pesan = (
            "⚠️ **Format tanggal tidak valid.**\n\n"
            "Kamu bisa gunakan:\n"
            "• Format angka: `22-08-2026`\n"
            "• Format teks bulan: `12 september 2026`, `september 12 2026`\n"
            "• Hari: `senin`-`minggu`, `hari ini`, `besok`, `lusa`\n\n"
            "💡 Contoh: `/tambahagenda Rapat Ormawa | 12 september 2026 | 16:00 di Gedung B`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    tanggal_str = parsed_date

    # Jika user memasukkan jam di bagian tanggal (contoh: besok 16:00)
    if parsed_time:
        if keterangan == "Tanpa keterangan":
            keterangan = f"Pukul {parsed_time} WIB"
        elif parsed_time not in keterangan:
            keterangan = f"Pukul {parsed_time} WIB | {keterangan}"

    agenda_list = load_agenda_data()
    next_id = max([a.get("id", 0) for a in agenda_list], default=0) + 1

    agenda_baru = {
        "id": next_id,
        "nama_acara": nama_acara,
        "tanggal": tanggal_str,
        "keterangan": keterangan,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    agenda_list.append(agenda_baru)
    if save_agenda_data(agenda_list):
        try:
            dt_obj = datetime.strptime(tanggal_str, "%d-%m-%Y")
            hari_nama = HARI_INDONESIA.get(dt_obj.weekday(), "").title()
            tanggal_info = f"{tanggal_str} ({hari_nama})"
        except Exception:
            tanggal_info = tanggal_str

        pesan = (
            f"✅ **Agenda Berhasil Dicatat!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📌 **Acara:** {nama_acara}\n"
            f"📅 **Tanggal:** {tanggal_info}\n"
            f"📍 **Keterangan:** {keterangan}\n\n"
            "Ketik `/agenda` untuk melihat semua agenda mendatang."
        )
    else:
        pesan = "❌ Gagal menyimpan agenda ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def agenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /agenda (melihat seluruh agenda mendatang)"""
    agenda_list = load_agenda_data()
    if not agenda_list:
        await update.message.reply_text("🎉 **Tidak ada agenda khusus!** Jadwalmu bebas dari acara tambahan.", parse_mode="Markdown")
        return

    today_dt = get_now_wib().date()
    pesan = "📅 **DAFTAR AGENDA & KEGIATAN MENDATANG**:\n\n"

    for a in agenda_list:
        tanggal_str = a.get("tanggal", "")
        status = ""
        hari_info = ""
        try:
            tanggal_dt = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
            hari_nama = HARI_INDONESIA.get(tanggal_dt.weekday(), "").title()
            hari_info = f" ({hari_nama})"
            selisih_hari = (tanggal_dt - today_dt).days
            if selisih_hari < 0:
                status = "*(🔴 Sudah Lewat)*"
            elif selisih_hari == 0:
                status = "*(🚨 HARI INI!)*"
            elif selisih_hari == 1:
                status = "*(⚠️ BESOK!)*"
            else:
                status = f"*(🗓️ {selisih_hari} hari lagi)*"
        except ValueError:
            pass

        pesan += f"• 🆔 `#{a.get('id')}` : **{a.get('nama_acara')}** {status}\n"
        pesan += f"  📅 Tanggal : {tanggal_str}{hari_info}\n"
        pesan += f"  📍 Info    : {a.get('keterangan', '-')}\n"
        pesan += "----------------------------\n"

    pesan += "\n💡 *Gunakan `/hapusagenda [ID]` jika acara sudah selesai.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def hapusagenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /hapusagenda [ID 1] [ID 2] ... (bisa multi-ID)"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Masukkan ID agenda yang ingin dihapus.\n\n"
            "💡 **Contoh:**\n"
            "• Satu agenda: `/hapusagenda 1`\n"
            "• Banyak agenda: `/hapusagenda 1 2 3`",
            parse_mode="Markdown"
        )
        return

    raw_tokens = " ".join(context.args).replace(",", " ").split()
    target_ids = []
    for token in raw_tokens:
        clean = token.replace("#", "")
        if clean.isdigit():
            target_ids.append(int(clean))

    if not target_ids:
        await update.message.reply_text("⚠️ ID agenda harus berupa angka. Contoh: `/hapusagenda 1`", parse_mode="Markdown")
        return

    unique_target_ids = list(dict.fromkeys(target_ids))
    agenda_list = load_agenda_data()

    berhasil_dihapus = []
    sisa_agenda = []

    target_ids_set = set(unique_target_ids)
    for a in agenda_list:
        if a.get("id") in target_ids_set:
            berhasil_dihapus.append(a)
        else:
            sisa_agenda.append(a)

    if not berhasil_dihapus:
        daftar_id = ", ".join([f"`#{tid}`" for tid in unique_target_ids])
        await update.message.reply_text(f"❌ Agenda dengan ID {daftar_id} tidak ditemukan.", parse_mode="Markdown")
        return

    save_agenda_data(sisa_agenda)

    if len(berhasil_dihapus) == 1:
        item = berhasil_dihapus[0]
        pesan = (
            f"🎉 **Agenda Selesai / Dihapus:**\n\n"
            f"📌 *{item.get('nama_acara')}* ({item.get('tanggal')})\n\n"
            "Item telah dihapus dari daftar agenda aktif."
        )
    else:
        daftar_teks = "\n".join([f"• 📌 *{item.get('nama_acara')}* ({item.get('tanggal')})" for item in berhasil_dihapus])
        pesan = (
            f"🎉 **{len(berhasil_dihapus)} Agenda Selesai / Dihapus:**\n\n"
            f"{daftar_teks}\n\n"
            "Item telah dihapus dari daftar agenda aktif."
        )

    await update.message.reply_text(pesan, parse_mode="Markdown")
