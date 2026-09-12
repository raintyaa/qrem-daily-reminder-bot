import asyncio
from datetime import datetime, timedelta
from config import HARI_INDONESIA, get_now_wib
from storage import (
    load_jadwal_data,
    load_tugas_data,
    load_agenda_data,
    load_subscribers,
)
from utils import (
    normalize_rutinitas_item,
    should_remind_task,
    get_task_deadline_dt,
    generate_daily_briefing,
    cleanup_expired_tasks,
    is_rutinitas_active_on_day,
)

async def auto_reminder_loop(app) -> None:
    """Loop latar belakang yang otomatis mengirim briefing pagi & alarm pengingat tepat waktu"""
    briefing_terakhir = None
    rutinitas_terkirim = set()
    kuliah_terkirim = set()
    tugas_h_terkirim = set()
    tugas_berkala_terakhir = None
    agenda_terkirim = set()

    while True:
        try:
            now = get_now_wib()
            today_date = now.date()
            current_time_str = now.strftime("%H:%M")

            # 1. Briefing Harian Pagi (Jam 05:00 WIB)
            if now.hour == 5 and briefing_terakhir != today_date:
                subscribers = load_subscribers()
                if subscribers:
                    pesan = generate_daily_briefing()
                    for chat_id in subscribers:
                        try:
                            await app.bot.send_message(chat_id=chat_id, text=pesan, parse_mode="Markdown")
                            print(f"[scheduler] Briefing pagi terkirim ke {chat_id}")
                        except Exception as e:
                            print(f"[Scheduler] Gagal kirim briefing ke {chat_id}: {e}")
                    briefing_terakhir = today_date

            jadwal_data = load_jadwal_data()
            raw_rutinitas = jadwal_data.get("rutinitas", [])
            rutinitas_list = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
            hari_index = now.weekday()
            hari_ini = HARI_INDONESIA.get(hari_index, "senin")

            # 2. Alarm Rutinitas (Setiap Hari atau Hari Spesifik)
            for r in rutinitas_list:
                r_hari = r.get("hari", "setiap hari")
                r_jam = r.get("jam", "00:00")
                r_kegiatan = r.get("kegiatan", "-")
                r_id = r.get("id", 0)

                if is_rutinitas_active_on_day(r_hari, hari_ini):
                    key_rutinitas = f"{today_date}_{r_id}_{r_jam}"
                    if current_time_str == r_jam and key_rutinitas not in rutinitas_terkirim:
                        subscribers = load_subscribers()
                        print(f"[Scheduler] Pukul {current_time_str}: Waktu cocok! Mengirim rutinitas '{r_kegiatan}' ke: {subscribers}")
                        if subscribers:
                            label_hari = f" ({r_hari.title()})" if r_hari != "setiap hari" else ""
                            pesan_rutinitas = (
                                f"⏰ **PENGINGAT RUTINITAS ({r_jam} WIB)**\n\n"
                                f"🔔 *Waktunya:* **{r_kegiatan}**{label_hari}\n\n"
                                f"💡 *Ketik `/beresrutinitas {r_id}` jika sudah selesai!*"
                            )
                            for chat_id in subscribers:
                                try:
                                    await app.bot.send_message(chat_id=chat_id, text=pesan_rutinitas, parse_mode="Markdown")
                                    print(f"[Scheduler] ✅ Berhasil mengirim alarm rutinitas ke {chat_id}")
                                except Exception as e:
                                    print(f"[Scheduler] ❌ Gagal kirim alarm rutinitas ke {chat_id}: {e}")
                        rutinitas_terkirim.add(key_rutinitas)

            if len(rutinitas_terkirim) > 50:
                rutinitas_terkirim.clear()

            # 3. Alarm Pengingat Kuliah (1 Jam Sebelum Kelas)
            jadwal_hari_ini = jadwal_data.get("jadwal", {}).get(hari_ini, [])
            for matkul_item in jadwal_hari_ini:
                jam_raw = matkul_item.get("jam", "")
                if "-" in jam_raw:
                    jam_mulai = jam_raw.split("-")[0].strip().replace(".", ":")
                    if len(jam_mulai.split(":")[0]) == 1:
                        jam_mulai = "0" + jam_mulai
                    try:
                        t_mulai = datetime.strptime(jam_mulai, "%H:%M")
                        t_pengingat = (datetime.combine(today_date, t_mulai.time()) - timedelta(hours=1)).time()
                        jam_pengingat = t_pengingat.strftime("%H:%M")
                    except Exception:
                        jam_pengingat = jam_mulai

                    key_kuliah = f"{today_date}_kuliah_{jam_mulai}_{matkul_item.get('matkul')}"
                    if current_time_str == jam_pengingat and key_kuliah not in kuliah_terkirim:
                        subscribers = load_subscribers()
                        print(f"[Scheduler] Pukul {current_time_str}: Waktu pengingat kuliah cocok (1 jam sebelum {jam_mulai})! Mengirim '{matkul_item.get('matkul')}'...")
                        if subscribers:
                            pesan_kuliah = (
                                f"🔔 **PENGINGAT KULIAH (1 Jam Lagi - {jam_mulai})** 🔔\n\n"
                                f"📚 **Mata Kuliah:** {matkul_item.get('matkul')}\n"
                                f"🏫 **Kelas:** {matkul_item.get('kelas', '-')}\n"
                                f"📍 **Ruang:** {matkul_item.get('ruang', '-')}\n"
                                f"⏰ **Waktu Kuliah:** {jam_raw}\n\n"
                                "Yuk siap-siap ke kampus! 🚀"
                            )
                            for chat_id in subscribers:
                                try:
                                    await app.bot.send_message(chat_id=chat_id, text=pesan_kuliah, parse_mode="Markdown")
                                    print(f"[Scheduler] ✅ Berhasil kirim pengingat kuliah ke {chat_id}")
                                except Exception as e:
                                    print(f"[Scheduler] ❌ Gagal kirim pengingat kuliah ke {chat_id}: {e}")
                        kuliah_terkirim.add(key_kuliah)

            if len(kuliah_terkirim) > 30:
                kuliah_terkirim.clear()

            # 4. Pengingat Tugas Kuliah:
            # 4A. Hari H Deadline (Tepat 6 Jam Sebelum Jam Batas Waktu)
            cleanup_expired_tasks(now)
            tugas_list = load_tugas_data()
            for t in tugas_list:
                if not should_remind_task(t):
                    continue
                deadline_dt = get_task_deadline_dt(t)
                if not deadline_dt:
                    continue

                if deadline_dt.date() == today_date:
                    reminder_target_dt = deadline_dt - timedelta(hours=6)
                    if now.hour == reminder_target_dt.hour and now.minute == reminder_target_dt.minute:
                        key_tugas_h = f"{today_date}_h6_{t.get('id')}_{now.hour}_{now.minute}"
                        if key_tugas_h not in tugas_h_terkirim:
                            subscribers = load_subscribers()
                            if subscribers:
                                jam_deadline_str = t.get("jam", "-")
                                jam_display = f"Pukul {jam_deadline_str} WIB" if jam_deadline_str != "-" else "Pukul 23:59 WIB (Akhir Hari)"
                                pesan_h = (
                                    "🚨 **PENGINGAT DEADLINE TUGAS (6 JAM LAGI!)** 🚨\n\n"
                                    f"📝 **Tugas:** {t.get('nama_tugas')}\n"
                                    f"📕 **Matkul:** {t.get('matkul')}\n"
                                    f"⏰ **Batas Waktu:** {jam_display} Hari Ini!\n\n"
                                    "⚡ *Ayo dikebut, batas waktunya udah mepet!*\n"
                                    f"💡 Ketik `/selesai {t.get('id')}` jika sudah selesai."
                                )
                                for chat_id in subscribers:
                                    try:
                                        await app.bot.send_message(chat_id=chat_id, text=pesan_h, parse_mode="Markdown")
                                        print(f"[Scheduler] ✅ Berhasil kirim pengingat H-6 jam tugas #{t.get('id')} ke {chat_id}")
                                    except Exception as e:
                                        print(f"[Scheduler] ❌ Gagal kirim pengingat tugas H-6 jam: {e}")
                            tugas_h_terkirim.add(key_tugas_h)

            if len(tugas_h_terkirim) > 50:
                tugas_h_terkirim.clear()

            # 4B. Sebelum Hari H: Pengingat Berkala Setiap 6 Jam (Pukul 06:00, 12:00, 18:00 WIB)
            if now.hour in (6, 12, 18) and now.minute == 0:
                slot_berkala_key = f"{today_date}_{now.hour}"
                if slot_berkala_key != tugas_berkala_terakhir:
                    tugas_mendatang = []
                    for t in tugas_list:
                        if not should_remind_task(t):
                            continue
                        deadline_dt = get_task_deadline_dt(t)
                        if not deadline_dt:
                            continue

                        if deadline_dt.date() > today_date:
                            selisih_hari = (deadline_dt.date() - today_date).days
                            if selisih_hari == 1:
                                status = "⚠️ *BESOK!*"
                            elif selisih_hari <= 3:
                                status = f"⏳ *{selisih_hari} hari lagi*"
                            elif selisih_hari <= 7:
                                status = f"🗓️ *{selisih_hari} hari lagi*"
                            else:
                                status = f"📅 *{selisih_hari} hari lagi*"

                            jam_str = t.get("jam", "-")
                            jam_info = f" • Pukul {jam_str} WIB" if jam_str and jam_str != "-" else ""
                            tugas_mendatang.append({
                                "selisih": selisih_hari,
                                "teks": f"• 📝 **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {t.get('deadline')}{jam_info} ({status})"
                            })

                    tugas_mendatang.sort(key=lambda x: x["selisih"])

                    if tugas_mendatang:
                        subscribers = load_subscribers()
                        jam_slot_str = f"{now.hour:02d}:00"
                        daftar_teks = "\n\n".join([item["teks"] for item in tugas_mendatang])
                        pesan_berkala = (
                            f"📋 **PENGINGAT TUGAS BERKALA (Pukul {jam_slot_str} WIB)** 📋\n\n"
                            "Ini daftar tugas mendatang yang perlu dicicil:\n\n"
                            f"{daftar_teks}\n\n"
                            "💡 *Cicil dari sekarang biar nggak numpuk pas deadline!*\n"
                            "Ketik `/selesai [ID]` jika tugas sudah beres."
                        )
                        for chat_id in subscribers:
                            try:
                                await app.bot.send_message(chat_id=chat_id, text=pesan_berkala, parse_mode="Markdown")
                                print(f"[Scheduler] ✅ Berhasil kirim pengingat tugas berkala {jam_slot_str} ke {chat_id}")
                            except Exception as e:
                                print(f"[Scheduler] ❌ Gagal kirim pengingat tugas berkala: {e}")

                    tugas_berkala_terakhir = slot_berkala_key            

            # 5. Alarm Pengingat Agenda Acara Hari H (Jam 05:00 Pagi)
            if now.hour == 5 and now.minute == 0:
                agenda_list = load_agenda_data()
                for a in agenda_list:
                    tanggal_str = a.get("tanggal", "")
                    keterangan_str = a.get("keterangan", "")

                    if tanggal_str == today_date.strftime("%d-%m-%Y"):
                        key_agenda = f"{today_date}_agenda_{a.get('id')}"
                        if key_agenda not in agenda_terkirim:
                            subscribers = load_subscribers()
                            print(f"[Scheduler] Pukul 05:00: Mengirim pengingat agenda hari H '{a.get('nama_acara')}'...")
                            if subscribers:
                                pesan_agenda = (
                                    f"🔔 **PENGINGAT AGENDA HARI INI (05:00 Pagi)** 🔔\n\n"
                                    f"📌 **Acara:** {a.get('nama_acara')}\n"
                                    f"📍 **Info/Lokasi:** {keterangan_str}\n\n"
                                    "Jangan sampai kelewat, hari ini ada agenda ini! ✨"
                                )
                                for chat_id in subscribers:
                                    try:
                                        await app.bot.send_message(chat_id=chat_id, text=pesan_agenda, parse_mode="Markdown")
                                        print(f"[Scheduler] ✅ Berhasil kirim alarm agenda hari H ke {chat_id}")
                                    except Exception as e:
                                        print(f"[Scheduler] ❌ Gagal kirim alarm agenda hari H: {e}")
                                agenda_terkirim.add(key_agenda)

            if len(agenda_terkirim) > 30:
                agenda_terkirim.clear()

        except Exception as err:
            print(f"[Scheduler Error] {err}")

        await asyncio.sleep(25)
