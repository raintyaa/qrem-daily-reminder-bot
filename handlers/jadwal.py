from telegram import Update
from telegram.ext import ContextTypes
from config import HARI_INDONESIA, get_now_wib
from storage import (
    load_jadwal_data,
    save_jadwal_data,
    load_rutinitas_selesai_data,
    save_rutinitas_selesai_data,
)
from utils import (
    format_jadwal_hari,
    normalize_rutinitas_item,
    is_valid_time,
    normalize_time,
    is_rutinitas_active_on_day,
    parse_hari_rutinitas,
    ORDER_HARI,
)

async def jadwal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /jadwal [hari/semua]"""
    data = load_jadwal_data()
    jadwal = data.get("jadwal", {})

    if context.args:
        pilihan = context.args[0].lower()
        if pilihan in ("semua", "all", "pekan"):
            pesan_list = ["📚 **JADWAL KULIAH SEPEKAN**\n"]
            for hari in ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]:
                if hari in jadwal and jadwal[hari]:
                    pesan_list.append(format_jadwal_hari(hari, jadwal[hari]))
            pesan = "\n---\n\n".join(pesan_list)
        elif pilihan in HARI_INDONESIA.values():
            list_matkul = jadwal.get(pilihan, [])
            pesan = format_jadwal_hari(pilihan, list_matkul)
        else:
            pesan = (
                "⚠️ Nama hari tidak dikenali.\n"
                "Contoh penggunaan:\n"
                "• `/jadwal` (hari ini)\n"
                "• `/jadwal senin`\n"
                "• `/jadwal semua`"
            )
    else:
        hari_index = get_now_wib().weekday()
        hari_ini = HARI_INDONESIA.get(hari_index, "senin")
        list_matkul = jadwal.get(hari_ini, [])
        pesan = f"🔔 *Hari ini: {hari_ini.capitalize()}*\n\n" + format_jadwal_hari(hari_ini, list_matkul)

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def rutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /rutinitas [hari/semua]"""
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
    selesai_ids = load_rutinitas_selesai_data()

    if not rutinitas:
        await update.message.reply_text("📝 Belum ada daftar rutinitas yang tersimpan.\nGunakan `/tambahrutinitas` untuk menambah.", parse_mode="Markdown")
        return

    hari_index = get_now_wib().weekday()
    hari_ini = HARI_INDONESIA.get(hari_index, "senin")

    if context.args:
        pilihan = context.args[0].lower()
        if pilihan in ("semua", "all", "daftar"):
            pesan = "⏰ **DAFTAR SELURUH RUTINITAS (SEMUA HARI)**:\n\n"
            for r in rutinitas:
                status = " *(✅ Selesai Hari Ini)*" if r["id"] in selesai_ids else ""
                hari_tag = f"[{r['hari'].title()}]"
                pesan += f"• 🆔 `#{r['id']}` {hari_tag} Pukul {r['jam']} WIB:\n  🔔 **{r['kegiatan']}**{status}\n"
            pesan += "\n💡 *Gunakan `/tambahrutinitas` atau `/hapusrutinitas [ID]` untuk mengelola.*"
            await update.message.reply_text(pesan, parse_mode="Markdown")
            return
        elif pilihan in HARI_INDONESIA.values() or pilihan == "setiap hari":
            target_hari = pilihan
        else:
            await update.message.reply_text("⚠️ Nama hari tidak dikenali. Contoh: `/rutinitas`, `/rutinitas jumat`, atau `/rutinitas semua`", parse_mode="Markdown")
            return
    else:
        target_hari = hari_ini

    daftar_hari = [r for r in rutinitas if is_rutinitas_active_on_day(r["hari"], target_hari)]
    daftar_hari.sort(key=lambda x: x["jam"])

    if not daftar_hari:
        pesan = f"⏰ **Rutinitas Hari {target_hari.capitalize()}**:\n*Tidak ada kegiatan rutinitas khusus di hari ini.*"
    else:
        pesan = f"⏰ **Daftar Rutinitas - {target_hari.capitalize()}**:\n\n"
        for r in daftar_hari:
            status = " *(✅ Selesai Hari Ini)*" if r["id"] in selesai_ids else ""
            label_hari = ""
            if r["hari"] in ("setiap hari", "semua", "daily", "all"):
                label_hari = " (Setiap Hari)"
            elif "," in r["hari"]:
                label_hari = f" ({r['hari'].title()})"
            pesan += f"• 🆔 `#{r['id']}` Pukul **{r['jam']} WIB**{label_hari}:\n  🔔 {r['kegiatan']}{status}\n"

        pesan += "\n💡 *Gunakan `/beresrutinitas [ID]` untuk mencoret rutinitas yang selesai hari ini.*"

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def beresrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /beresrutinitas [ID 1] [ID 2] ... (bisa banyak ID & urutan acak)"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Masukkan ID rutinitas yang ingin dicoret.\n\n"
            "💡 **Contoh:**\n"
            "• Satu rutinitas: `/beresrutinitas 1`\n"
            "• Banyak rutinitas (urutan acak): `/beresrutinitas 3 1 4 2`",
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
        await update.message.reply_text(
            "⚠️ ID rutinitas harus berupa angka.\nContoh: `/beresrutinitas 1 2 3`",
            parse_mode="Markdown"
        )
        return
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
    rutinitas_map = {r["id"]: r for r in rutinitas}
    selesai_list = load_rutinitas_selesai_data()
    berhasil_dicoret = []
    sudah_selesai_sebelumnya = []
    tidak_ditemukan = []

    unique_target_ids = list(dict.fromkeys(target_ids))

    for tid in unique_target_ids:
        if tid in rutinitas_map:
            item = rutinitas_map[tid]
            if tid not in selesai_list:
                selesai_list.append(tid)
                berhasil_dicoret.append(item)
            else:
                sudah_selesai_sebelumnya.append(item)
        else:
            tidak_ditemukan.append(tid)
    
    if berhasil_dicoret:
        save_rutinitas_selesai_data(selesai_list)
        berhasil_dicoret.sort(key=lambda x: x["jam"])

    pesan_bagian = []

    if berhasil_dicoret:
        if len(berhasil_dicoret) == 1:
            item = berhasil_dicoret[0]
            pesan_bagian.append(
                f"🎉 **Bagus! Rutinitas Beres Hari Ini:**\n\n"
                f"✅ *{item['kegiatan']}* (Pukul {item['jam']} WIB)"
            )
        else:
            daftar_teks = "\n".join([f"• ✅ *{item['kegiatan']}* (Pukul {item['jam']} WIB)" for item in berhasil_dicoret])
            pesan_bagian.append(
                f"🎉 **Bagus! {len(berhasil_dicoret)} Rutinitas Beres Hari Ini:**\n\n"
                f"{daftar_teks}"
            )
    if sudah_selesai_sebelumnya:
        daftar_sudah = ", ".join([f"`#{item['id']}` ({item['kegiatan']})" for item in sudah_selesai_sebelumnya])
        pesan_bagian.append(f"ℹ️ *Sudah dicoret sebelumnya:* {daftar_sudah}")
    if tidak_ditemukan:
        daftar_hilang = ", ".join([f"`#{tid}`" for tid in tidak_ditemukan])
        pesan_bagian.append(f"❌ *ID tidak ditemukan:* {daftar_hilang}\n(Ketik `/rutinitas` untuk melihat daftar ID yang tersedia)")
    pesan_bagian.append("\nStatus ini akan otomatis di-reset besok pagi.")
    pesan_final = "\n\n".join(pesan_bagian)
    await update.message.reply_text(pesan_final, parse_mode="Markdown")

async def tambahrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahrutinitas [Hari] | [Jam] | [Keterangan]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda '|' (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahrutinitas [Hari] | [Jam HH:MM] | [Keterangan Kegiatan]`\n\n"
            "💡 **Pilihan Hari:**\n"
            "• `setiap hari` (berlaku tiap hari)\n"
            "• Hari spesifik: `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n"
            "• Multi-hari: `senin, kamis` atau `selasa & jumat`\n\n"
            "💡 **Contoh:**\n"
            "• `/tambahrutinitas setiap hari | 04:30 | Bangun pagi & salat subuh`\n"
            "• `/tambahrutinitas senin, kamis | 07:00 | Jogging pagi`\n"
            "• `/tambahrutinitas jumat | 11:30 | Persiapan salat Jumat`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    bagian = [b.strip() for b in input_teks.split("|")]
    if len(bagian) < 3:
        await update.message.reply_text("⚠️ Format kurang lengkap! Pastikan mengisi: `Hari | Jam | Keterangan`", parse_mode="Markdown")
        return

    hari_raw = bagian[0]
    jam_raw = bagian[1]
    kegiatan = bagian[2]

    hari_final = parse_hari_rutinitas(hari_raw)
    if not hari_final:
        await update.message.reply_text(
            "⚠️ **Pilihan hari tidak valid!**\n\n"
            "Kamu bisa memasukkan:\n"
            "• `setiap hari`\n"
            "• Hari spesifik: `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n"
            "• Gabungan hari: `senin, kamis` atau `selasa & jumat`",
            parse_mode="Markdown"
        )
        return

    if not is_valid_time(jam_raw):
        await update.message.reply_text("⚠️ Format jam tidak valid! Gunakan format **HH:MM** (contoh: `04:30` atau `19:00`).", parse_mode="Markdown")
        return

    jam_final = normalize_time(jam_raw)

    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]

    next_id = max([r.get("id", 0) for r in rutinitas], default=0) + 1

    item_baru = {
        "id": next_id,
        "hari": hari_final,
        "jam": jam_final,
        "kegiatan": kegiatan
    }

    rutinitas.append(item_baru)
    data["rutinitas"] = rutinitas

    if save_jadwal_data(data):
        pesan = (
            f"✅ **Rutinitas Berhasil Ditambahkan!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📅 **Hari:** {hari_final.title()}\n"
            f"⏰ **Waktu:** {jam_final} WIB\n"
            f"🔔 **Kegiatan:** {kegiatan}\n\n"
            "Ketik `/rutinitas` untuk melihat daftar rutinitas."
        )
    else:
        pesan = "❌ Gagal menyimpan rutinitas ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def hapusrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /hapusrutinitas.
    Mendukung:
    - Hapus permanen: `/hapusrutinitas 1` atau `/hapusrutinitas 1 2 3`
    - Hapus hari tertentu saja: `/hapusrutinitas 1 jumat` atau `/hapusrutinitas 1 senin, kamis`
    """
    if not context.args:
        pesan = (
            "⚠️ **Format Perintah Hapus Rutinitas:**\n\n"
            "• **Hapus Semua Hari:**\n"
            "  `/hapusrutinitas [ID]` (contoh: `/hapusrutinitas 1`)\n"
            "  `/hapusrutinitas [ID 1] [ID 2]` (contoh: `/hapusrutinitas 1 2 3`)\n\n"
            "• **Hapus Hari Tertentu Saja:**\n"
            "  `/hapusrutinitas [ID] [Hari]`\n"
            "  (contoh: `/hapusrutinitas 1 jumat` atau `/hapusrutinitas 1 senin, kamis`)"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    raw_input = " ".join(context.args)
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
    rutinitas_map = {r["id"]: r for r in rutinitas}

    tokens = raw_input.replace("|", " ").replace(",", " ").split()
    day_tokens = []
    numeric_tokens = []

    for token in tokens:
        clean = token.replace("#", "").lower().strip()
        if clean.isdigit():
            numeric_tokens.append(int(clean))
        else:
            t_day = clean
            if t_day.startswith("hari"):
                t_day = t_day[4:].strip()
            if t_day in ORDER_HARI:
                if t_day not in day_tokens:
                    day_tokens.append(t_day)

    # KASUS A: Menghapus hari tertentu dari suatu rutinitas
    if day_tokens:
        if not numeric_tokens:
            await update.message.reply_text(
                "⚠️ Masukkan ID rutinitas yang harinya ingin dicopot.\nContoh: `/hapusrutinitas 1 jumat`",
                parse_mode="Markdown"
            )
            return

        target_id = numeric_tokens[0]
        if target_id not in rutinitas_map:
            await update.message.reply_text(
                f"❌ Rutinitas dengan ID `#{target_id}` tidak ditemukan.\nKetik `/rutinitas semua` untuk melihat daftar ID.",
                parse_mode="Markdown"
            )
            return

        item = rutinitas_map[target_id]
        current_hari = item.get("hari", "setiap hari").lower()

        if current_hari in ("setiap hari", "semua", "all", "daily"):
            active_days = list(ORDER_HARI)
        else:
            active_days = [d.strip() for d in current_hari.split(",") if d.strip()]

        matched_remove = [d for d in day_tokens if d in active_days]
        if not matched_remove:
            hari_hapus_str = ", ".join([d.title() for d in day_tokens])
            await update.message.reply_text(
                f"ℹ️ Rutinitas `#{target_id}` (**{item.get('kegiatan')}**) memang tidak aktif pada hari: {hari_hapus_str}.\n"
                f"📅 Jadwal saat ini: **{current_hari.title()}**",
                parse_mode="Markdown"
            )
            return

        remaining_days = [d for d in active_days if d not in matched_remove]

        if not remaining_days:
            sisa_rutinitas = [r for r in rutinitas if r["id"] != target_id]
            data["rutinitas"] = sisa_rutinitas
            if save_jadwal_data(data):
                await update.message.reply_text(
                    f"🗑️ **Rutinitas Dihapus Sepenuhnya:**\n\n"
                    f"Karena seluruh harinya ({', '.join([d.title() for d in matched_remove])}) telah dicopot, "
                    f"rutinitas `#{target_id}` (**{item.get('kegiatan')}**) dihapus dari database.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Gagal memperbarui rutinitas ke database.", parse_mode="Markdown")
            return

        remaining_days.sort(key=lambda d: ORDER_HARI.index(d))
        new_hari_str = ", ".join(remaining_days)
        item["hari"] = new_hari_str
        data["rutinitas"] = rutinitas

        if save_jadwal_data(data):
            hari_copot_str = ", ".join([d.title() for d in matched_remove])
            pesan = (
                f"✅ **Hari Rutinitas Berhasil Diperbarui!**\n\n"
                f"• 🆔 `#{target_id}`: **{item.get('kegiatan')}** (Pukul {item.get('jam')} WIB)\n"
                f"• ❌ Hari dicopot: {hari_copot_str}\n"
                f"• 📅 Jadwal aktif sekarang: **{new_hari_str.title()}**"
            )
        else:
            pesan = "❌ Gagal memperbarui rutinitas ke database."

        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    # KASUS B: Menghapus permanen (satu atau banyak ID sekaligus)
    if not numeric_tokens:
        await update.message.reply_text(
            "⚠️ ID rutinitas harus berupa angka.\nContoh: `/hapusrutinitas 1` atau `/hapusrutinitas 1 2 3`",
            parse_mode="Markdown"
        )
        return

    unique_target_ids = list(dict.fromkeys(numeric_tokens))
    berhasil_dihapus = []
    tidak_ditemukan = []
    sisa_rutinitas = []

    target_ids_set = set(unique_target_ids)
    for r in rutinitas:
        if r["id"] in target_ids_set:
            berhasil_dihapus.append(r)
        else:
            sisa_rutinitas.append(r)

    for tid in unique_target_ids:
        if tid not in rutinitas_map:
            tidak_ditemukan.append(tid)

    if not berhasil_dihapus:
        daftar_hilang = ", ".join([f"`#{tid}`" for tid in tidak_ditemukan])
        await update.message.reply_text(
            f"❌ Rutinitas dengan ID {daftar_hilang} tidak ditemukan.\nKetik `/rutinitas semua` untuk melihat daftar ID.",
            parse_mode="Markdown"
        )
        return

    data["rutinitas"] = sisa_rutinitas
    if save_jadwal_data(data):
        pesan_list = []
        if len(berhasil_dihapus) == 1:
            item = berhasil_dihapus[0]
            pesan_list.append(
                f"🗑️ **Rutinitas Berhasil Dihapus:**\n\n"
                f"• 🆔 `#{item.get('id')}`: **{item.get('kegiatan')}**\n"
                f"  ⏰ {item.get('hari').title()} pukul {item.get('jam')} WIB"
            )
        else:
            daftar_teks = "\n".join([
                f"• 🆔 `#{item.get('id')}`: **{item.get('kegiatan')}** ({item.get('hari').title()} - {item.get('jam')} WIB)"
                for item in berhasil_dihapus
            ])
            pesan_list.append(
                f"🗑️ **{len(berhasil_dihapus)} Rutinitas Berhasil Dihapus:**\n\n"
                f"{daftar_teks}"
            )

        if tidak_ditemukan:
            daftar_hilang = ", ".join([f"`#{tid}`" for tid in tidak_ditemukan])
            pesan_list.append(f"\n⚠️ ID tidak ditemukan: {daftar_hilang}")

        pesan = "\n".join(pesan_list)
    else:
        pesan = "❌ Gagal menghapus rutinitas dari database."

    await update.message.reply_text(pesan, parse_mode="Markdown")
