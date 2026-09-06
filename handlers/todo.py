from telegram import Update
from telegram.ext import ContextTypes
from config import get_now_wib, HARI_INDONESIA
from storage import load_todo_data, save_todo_data
from utils import parse_hari_todo

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /todo [kegiatan] atau /todo [kegiatan] | [hari]"""
    input_teks = " ".join(context.args) if context.args else ""
    if not input_teks:
        pesan = (
            "⚠️ **Masukkan kegiatan to-do yang ingin dicatat!**\n\n"
            "📌 **Format:**\n"
            "• `/todo [Kegiatan]` *(default hari ini)*\n"
            "• `/todo [Kegiatan] | [Hari]`\n"
            "• `/todo [Hari] | [Kegiatan]`\n\n"
            "💡 **Pilihan Hari:**\n"
            "• Hari spesifik: `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n"
            "• Khusus: `hari ini`, `besok`, `setiap hari`\n\n"
            "💡 **Contoh:**\n"
            "• `/todo Beli binder dan pulpen`\n"
            "• `/todo Servis motor ke bengkel | kamis`\n"
            "• `/todo senin | Beli buku jarkom`\n"
            "• `/todo Olahraga pagi | setiap hari`\n"
            "• `/todo Cuci sepatu | besok`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    now_dt = get_now_wib()
    hari_ini_name = HARI_INDONESIA[now_dt.weekday()]

    if "|" in input_teks:
        bagian = [b.strip() for b in input_teks.split("|", 1)]
        part0, part1 = bagian[0], bagian[1]

        parsed_day_1 = parse_hari_todo(part1, now_dt)
        parsed_day_0 = parse_hari_todo(part0, now_dt)

        if parsed_day_1 is not None and part0:
            kegiatan = part0
            hari_final = parsed_day_1
        elif parsed_day_0 is not None and part1:
            kegiatan = part1
            hari_final = parsed_day_0
        else:
            await update.message.reply_text(
                "⚠️ **Hari tidak valid!**\n"
                "Pilih hari: `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`, `hari ini`, `besok`, atau `setiap hari`.\n\n"
                "💡 Contoh: `/todo Servis motor | kamis`",
                parse_mode="Markdown"
            )
            return
    else:
        kegiatan = input_teks
        hari_final = hari_ini_name

    todo_list = load_todo_data()
    next_id = max([t.get("id", 0) for t in todo_list], default=0) + 1

    item_baru = {
        "id": next_id,
        "kegiatan": kegiatan,
        "hari": hari_final,
        "dibuat_pada": now_dt.strftime("%Y-%m-%d %H:%M:%S")
    }

    todo_list.append(item_baru)
    if save_todo_data(todo_list):
        if hari_final in ("setiap hari", "semua"):
            label_hari = "Setiap Hari"
        elif hari_final == hari_ini_name:
            label_hari = f"{hari_final.title()} (Hari Ini)"
        else:
            label_hari = hari_final.title()

        pesan = (
            f"✅ **To-Do Berhasil Dicatat!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📌 **Kegiatan:** {kegiatan}\n"
            f"🗓️ **Target Hari:** {label_hari}\n\n"
            "Ketik `/listtodo` untuk melihat semua to-do aktif."
        )
    else:
        pesan = "❌ Gagal menyimpan to-do ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def listtodo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /listtodo atau /listtodo [hari/semua]"""
    todo_list = load_todo_data()
    if not todo_list:
        await update.message.reply_text("🎉 **Tidak ada to-do aktif!** Semua urusan harianmu sudah beres.", parse_mode="Markdown")
        return

    now_dt = get_now_wib()
    hari_ini_name = HARI_INDONESIA[now_dt.weekday()]

    arg_raw = " ".join(context.args).lower().strip() if context.args else "semua"

    if arg_raw in ("hari ini", "today"):
        filter_day = hari_ini_name
    elif arg_raw.startswith("hari "):
        filter_day = arg_raw[5:].strip()
    elif arg_raw in ("besok", "tomorrow"):
        filter_day = HARI_INDONESIA[(now_dt.weekday() + 1) % 7]
    else:
        filter_day = arg_raw

    if filter_day not in ("semua", "all"):
        hari_valid = set(HARI_INDONESIA.values()) | {"setiap hari", "semua", "all", "daily"}
        if filter_day not in hari_valid:
            await update.message.reply_text(
                "⚠️ **Pilihan hari tidak valid!**\n"
                "Gunakan: `/listtodo`, `/listtodo semua`, atau `/listtodo [senin-minggu]`\n\n"
                "💡 Contoh: `/listtodo senin` atau `/listtodo hari ini`",
                parse_mode="Markdown"
            )
            return

        filtered_todo = [
            t for t in todo_list
            if t.get("hari", "hari ini").lower() in (filter_day, "setiap hari", "semua", "all", "daily")
            or (t.get("hari", "").lower() == "hari ini" and filter_day == hari_ini_name)
        ]
        if not filtered_todo:
            await update.message.reply_text(
                f"🎉 **Tidak ada to-do untuk hari {filter_day.title()}!**",
                parse_mode="Markdown"
            )
            return

        pesan = f"📌 **DAFTAR TO-DO HARI {filter_day.upper()}**:\n\n"
        for item in filtered_todo:
            item_hari = item.get("hari", "hari ini").lower()
            tag_hari = " *(Setiap Hari)*" if item_hari in ("setiap hari", "semua", "all", "daily") else ""
            pesan += f"• 🆔 `#{item.get('id')}` : **{item.get('kegiatan', '-')}**{tag_hari}\n"
    else:
        pesan = "📌 **DAFTAR SELURUH TO-DO AKTIF**:\n\n"
        for item in todo_list:
            item_hari = item.get("hari", "hari ini").lower()
            if item_hari in ("setiap hari", "semua", "all", "daily"):
                label = "Setiap Hari"
            elif item_hari in (hari_ini_name, "hari ini"):
                label = f"{hari_ini_name.title()} (Hari Ini)"
            else:
                label = item_hari.title()
            pesan += f"• 🆔 `#{item.get('id')}` [🗓️ {label}] : **{item.get('kegiatan', '-')}**\n"

    pesan += "\n💡 *Gunakan `/berestodo [ID]` untuk mencoret to-do yang selesai.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def berestodo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /berestodo [ID 1] [ID 2] ... (bisa multi-ID)"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Masukkan ID to-do yang ingin dicoret.\n\n"
            "💡 **Contoh:**\n"
            "• Satu to-do: `/berestodo 1`\n"
            "• Banyak to-do: `/berestodo 1 2 3`",
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
        await update.message.reply_text("⚠️ ID to-do harus berupa angka. Contoh: `/berestodo 1`", parse_mode="Markdown")
        return

    unique_target_ids = list(dict.fromkeys(target_ids))
    todo_list = load_todo_data()

    berhasil_dicoret = []
    sisa_todo = []

    target_ids_set = set(unique_target_ids)
    for item in todo_list:
        if item.get("id") in target_ids_set:
            berhasil_dicoret.append(item)
        else:
            sisa_todo.append(item)

    if not berhasil_dicoret:
        daftar_id = ", ".join([f"`#{tid}`" for tid in unique_target_ids])
        await update.message.reply_text(f"❌ To-do dengan ID {daftar_id} tidak ditemukan.", parse_mode="Markdown")
        return

    save_todo_data(sisa_todo)

    if len(berhasil_dicoret) == 1:
        item = berhasil_dicoret[0]
        pesan = (
            f"🎉 **Bagus! To-Do Selesai & Dicoret:**\n\n"
            f"✅ *{item.get('kegiatan')}*\n\n"
            "Item telah dihapus dari daftar to-do aktif."
        )
    else:
        daftar_teks = "\n".join([f"• ✅ *{item.get('kegiatan')}*" for item in berhasil_dicoret])
        pesan = (
            f"🎉 **Bagus! {len(berhasil_dicoret)} To-Do Selesai & Dicoret:**\n\n"
            f"{daftar_teks}\n\n"
            "Item telah dihapus dari daftar to-do aktif."
        )

    await update.message.reply_text(pesan, parse_mode="Markdown")
