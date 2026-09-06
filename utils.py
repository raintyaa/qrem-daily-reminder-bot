from datetime import datetime, timedelta
from config import WIB, HARI_INDONESIA, get_now_wib
from storage import (
    load_jadwal_data,
    load_tugas_data,
    load_todo_data,
    load_agenda_data,
)

def is_valid_time(time_str: str) -> bool:
    """Memeriksa apakah string jam sesuai format HH:MM (00:00 - 23:59)."""
    if not time_str or time_str == "-":
        return False
    t_clean = time_str.strip().replace(".", ":")
    try:
        parts = t_clean.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except ValueError:
        return False

def normalize_time(time_str: str) -> str:
    """Mengubah format jam ke standar HH:MM (contoh: '9:00' -> '09:00', '23.59' -> '23:59')."""
    if not is_valid_time(time_str):
        return "-"
    t_clean = time_str.strip().replace(".", ":")
    parts = t_clean.split(":")
    h, m = int(parts[0]), int(parts[1])
    return f"{h:02d}:{m:02d}"

def normalize_rutinitas_item(item, default_id: int = 1) -> dict:
    """Menyeragamkan data rutinitas baik format teks lama maupun objek baru"""
    if isinstance(item, dict):
        return {
            "id": item.get("id", default_id),
            "hari": item.get("hari", "setiap hari").lower(),
            "jam": normalize_time(item.get("jam", "00:00")),
            "kegiatan": item.get("kegiatan", "-")
        }
    elif isinstance(item, str) and " - " in item:
        jam_part, nama_part = item.split(" - ", 1)
        return {
            "id": default_id,
            "hari": "setiap hari",
            "jam": normalize_time(jam_part.strip()),
            "kegiatan": nama_part.strip()
        }
    return {
        "id": default_id,
        "hari": "setiap hari",
        "jam": "00:00",
        "kegiatan": str(item)
    }

def parse_hari_todo(hari_str: str, now_dt: datetime = None) -> str | None:
    """
    Menormalisasi input hari untuk to-do.
    Mendukung:
    - Nama hari: 'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu' (opsional dengan awalan 'hari ')
    - Relatif: 'hari ini' / 'today' -> nama hari saat ini
    - 'besok' / 'tomorrow' -> nama hari esok
    - Berulang: 'setiap hari', 'tiap hari', 'daily', 'semua', 'all' -> 'setiap hari'
    """
    if not hari_str:
        return None
    raw = hari_str.lower().strip()
    if raw in ("setiap hari", "tiap hari", "daily", "semua", "all", "everyday"):
        return "setiap hari"

    if now_dt is None:
        now_dt = get_now_wib()

    if raw in ("hari ini", "today"):
        return HARI_INDONESIA[now_dt.weekday()]

    if raw in ("besok", "tomorrow"):
        return HARI_INDONESIA[(now_dt.weekday() + 1) % 7]

    if raw.startswith("hari "):
        raw = raw[5:].strip()

    if raw in HARI_INDONESIA.values():
        return raw

    return None

BULAN_MAP = {
    "januari": 1, "jan": 1, "january": 1,
    "februari": 2, "feb": 2, "february": 2,
    "maret": 3, "mar": 3, "march": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "agustus": 8, "agu": 8, "agt": 8, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12, "december": 12, "dec": 12    
}

def parse_deadline_input(raw_str: str) -> tuple[str | None, str | None]:
    """    Mengonversi input deadline teks bebas ke format standar (DD-MM-YYYY) dan jam (HH:MM).
    Mendukung format angka (12-09-2026) maupun teks acak:
    - 12 september 2026
    - 2026 september 12
    - september 12 2026
    """

    if not raw_str or raw_str.strip() == "-":
        return None, None
    
    cleaned = raw_str.strip().replace(",", " ")
    tokens = cleaned.split()

    found_time = None
    remaining_tokens = []

    for token in tokens:
        if is_valid_time(token):
            found_time = normalize_time(token)
        else:
            remaining_tokens.append(token)
    
    if not remaining_tokens:
        return None, None

    combined_lower = " ".join(remaining_tokens).lower().strip()

    # 1. Hari relatif
    if combined_lower in ("hari ini", "today"):
        return get_now_wib().strftime("%d-%m-%Y"), found_time
    if combined_lower in ("besok", "tomorrow"):
        return (get_now_wib() + timedelta(days=1)).strftime("%d-%m-%Y"), found_time
    if combined_lower in ("lusa",):
        return (get_now_wib() + timedelta(days=2)).strftime("%d-%m-%Y"), found_time

    # 2. Hari spesifik (senin, selasa, rabu, kamis, jumat, sabtu, minggu)
    day_name_clean = combined_lower
    if day_name_clean.startswith("hari "):
        day_name_clean = day_name_clean[5:].strip()

    day_to_index = {v: k for k, v in HARI_INDONESIA.items()}
    if day_name_clean in day_to_index:
        now_dt = get_now_wib()
        current_day_idx = now_dt.weekday()
        target_day_idx = day_to_index[day_name_clean]
        days_ahead = (target_day_idx - current_day_idx) % 7
        target_dt = now_dt + timedelta(days=days_ahead)
        return target_dt.strftime("%d-%m-%Y"), found_time

    if len(remaining_tokens) == 1:
        part = remaining_tokens[0]
        try:
            dt = datetime.strptime(part, "%d-%m-%Y")
            return dt.strftime("%d-%m-%Y"), found_time
        except ValueError:
            return None, None
    
    day = None
    month = None
    year = None

    for token in remaining_tokens:
        t_lower = token.lower().strip()
        if t_lower in BULAN_MAP:
            if month is None:
                month = BULAN_MAP[t_lower]
            else:
                return None, None
        elif t_lower.isdigit():
            val = int(t_lower)
            if val >= 1000:
                if year is None:
                    year = val
                else:
                    return None, None
            elif 1 <= val <= 31:
                if day is None:
                    day = val
                elif year is None:
                    year = 2000 + val if val < 100 else val
                else:
                    return None, None
            else:
                return None, None
        else:
            return None, None
    if day is not None and month is not None:
        if year is None:
            year = get_now_wib().year
        try:
            dt = datetime(year, month, day)
            return dt.strftime("%d-%m-%Y"), found_time
        except ValueError:
            return None, None

    return None, None

def is_valid_deadline(deadline: str) -> bool:
    """Memeriksa apakah deadline valid (mendukung format angka maupun nama bulan teks)."""
    date_str, _ = parse_deadline_input(deadline)
    return date_str is not None

def get_task_deadline_dt(t: dict) -> datetime | None:
    """Mengembalikan objek datetime deadline tugas dalam timezone WIB."""
    deadline_str = t.get("deadline", "")
    jam_str = t.get("jam", "-")
    if not deadline_str or deadline_str == "-":
        return None
    try:
        date_obj = datetime.strptime(deadline_str, "%d-%m-%Y").date()
        if jam_str and jam_str != "-" and is_valid_time(jam_str):
            time_clean = normalize_time(jam_str)
            h, m = map(int, time_clean.split(":"))
            return datetime(date_obj.year, date_obj.month, date_obj.day, h, m, tzinfo=WIB)
        else:
            # Default jika jam tidak ditentukan: akhir hari 23:59
            return datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, tzinfo=WIB)
    except Exception:
        return None

def should_remind_task(t: dict) -> bool:
    """Memeriksa apakah rentang waktu pembuatan tugas ke deadline minimal 6 jam."""
    deadline_dt = get_task_deadline_dt(t)
    if not deadline_dt:
        return False
    dibuat_pada_str = t.get("dibuat_pada")
    if not dibuat_pada_str:
        return True
    try:
        created_dt = datetime.strptime(dibuat_pada_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=WIB)
        selisih = deadline_dt - created_dt
        return selisih >= timedelta(hours=6)
    except Exception:
        return True

def format_jadwal_hari(hari: str, list_matkul: list) -> str:
    """Format tampilan jadwal untuk satu hari"""
    hari_title = hari.capitalize()
    if not list_matkul:
        return f"📅 **Jadwal {hari_title}**:\n*Libur / Tidak ada jadwal kelas.*"

    teks = f"📅 **Jadwal Kuliah - {hari_title}**:\n"
    for i, item in enumerate(list_matkul, 1):
        teks += f"\n{i}. **{item.get('matkul', '-')}**\n"
        teks += f"   ⏰ Waktu  : {item.get('jam', '-')}\n"
        teks += f"   📍 Ruang  : {item.get('ruang', '-')}\n"
        teks += f"   🏫 Kelas  : {item.get('kelas', '-')}\n"
    return teks

def generate_daily_briefing() -> str:
    """Merangkai pesan briefing harian: jadwal kuliah hari ini & status deadline tugas"""
    hari_index = get_now_wib().weekday()
    hari_ini = HARI_INDONESIA.get(hari_index, "senin")

    jadwal_data = load_jadwal_data()
    list_matkul = jadwal_data.get("jadwal", {}).get(hari_ini, [])

    pesan = f"☀️ **PENGINGAT HARIAN ({hari_ini.upper()})** ☀️\n\n"

    if list_matkul:
        pesan += "📚 **Jadwal Kuliah Hari Ini:**\n"
        for i, item in enumerate(list_matkul, 1):
            pesan += f"{i}. **{item.get('matkul')}** ({item.get('jam')})\n"
            pesan += f"   📍 Ruang: {item.get('ruang')} | Kelas: {item.get('kelas', '-')}\n"
    else:
        pesan += "🏖️ **Kuliah:** Hari ini libur / tidak ada jadwal kelas.\n"

    pesan += "\n----------------------------\n"

    tugas_list = load_tugas_data()
    today_dt = get_now_wib().date()
    tugas_mendesak = []

    for t in tugas_list:
        deadline_str = t.get("deadline", "")
        try:
            deadline_dt = datetime.strptime(deadline_str, "%d-%m-%Y").date()
            selisih_hari = (deadline_dt - today_dt).days

            if selisih_hari < 0:
                status = "🔴 *Lewat deadline!*"
            elif selisih_hari == 0:
                status = "🚨 *DEADLINE HARI INI!*"
            elif selisih_hari <= 1:
                status = "⚠️ *Deadline BESOK!*"
            elif selisih_hari <= 3:
                status = f"⏳ *{selisih_hari} hari lagi*"
            else:
                 status = f"🗓️ {selisih_hari} hari lagi"

            jam_str = t.get("jam", "-")
            jam_info = f" (Pukul {jam_str} WIB)" if jam_str and jam_str != "-" else ""
            tugas_mendesak.append(f"• **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {deadline_str}{jam_info} ({status})")
        except ValueError:
            continue

    if tugas_mendesak:
        pesan += "\n📝 **Status Tugas Kuliah:**\n" + "\n".join(tugas_mendesak)
    else:
        pesan += "\n🎉 **Tugas Kuliah:** Tidak ada tanggungan tugas saat ini!"

    todo_list = load_todo_data()
    if todo_list:
        todo_hari_ini = [
            item for item in todo_list
            if item.get("hari", "hari ini").lower() in (hari_ini, "hari ini", "setiap hari", "semua", "all", "daily")
        ]
        if todo_hari_ini:
            pesan += "\n----------------------------\n"
            pesan += f"\n📌 **Daftar To-Do Spontan Hari Ini ({hari_ini.title()}):**\n"
            for item in todo_hari_ini:
                tag_hari = ""
                if item.get("hari", "").lower() in ("setiap hari", "semua", "all", "daily"):
                    tag_hari = " *(Setiap Hari)*"
                pesan += f"• 🆔 `#{item.get('id')}`: {item.get('kegiatan')}{tag_hari}\n"

    agenda_list = load_agenda_data()
    if agenda_list:
        pesan += "\n----------------------------\n"
        pesan += "\n📅 **Daftar Seluruh Agenda Kegiatan:**\n"
        for a in agenda_list:
            tanggal_str = a.get("tanggal", "")
            status = ""
            try:
                tanggal_dt = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
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
            pesan += f"• **{a.get('nama_acara')}** {status}\n  📅 Tanggal: {tanggal_str} | 📍 Info: {a.get('keterangan', '-')}\n"

    return pesan
