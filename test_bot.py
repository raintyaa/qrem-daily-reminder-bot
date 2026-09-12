import os
from bot import (
    build_app,
    load_jadwal_data,
    format_jadwal_hari,
    load_tugas_data,
    save_tugas_data,
    load_todo_data,
    save_todo_data,
    load_agenda_data,
    save_agenda_data,
    is_valid_deadline,
    is_valid_time,
    normalize_time,
    save_jadwal_data,
    normalize_rutinitas_item,
    is_rutinitas_active_on_day,
    parse_hari_rutinitas,
    get_rutinitas_active_days,
    merge_rutinitas_days,
    find_rutinitas_conflict,
    reindex_rutinitas,
    generate_daily_briefing,
    cleanup_expired_tasks,
    load_subscribers,
    register_subscriber,
)

def test_handlers():
    """Memverifikasi seluruh handler terdaftar dengan benar"""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    app = build_app(dummy_token)
    
    handlers = app.handlers.get(0, [])
    commands = [h.commands for h in handlers if hasattr(h, 'commands')]
    flat_commands = {cmd for sublist in commands for cmd in sublist}
    
    expected_commands = {
        "start", "help", "jadwal", "rutinitas", "beresrutinitas",
        "tambahrutinitas", "hapusrutinitas",
        "tambahtugas", "listtugas", "selesai",
        "todo", "listtodo", "berestodo",
        "tambahagenda", "agenda", "hapusagenda",
        "cekpengingat"
    }
    for cmd in expected_commands:
        assert cmd in flat_commands, f"Handler /{cmd} tidak terdaftar!"
    
    print("[OK] Semua 17 handler terdaftar dengan benar.")

def test_jadwal_data():
    """Memverifikasi data jadwal dan rutinitas dapat dimuat dengan baik"""
    data = load_jadwal_data()
    assert "jadwal" in data, "Key 'jadwal' tidak ditemukan di data!"
    assert "rutinitas" in data, "Key 'rutinitas' tidak ditemukan di data!"
    
    senin_list = data["jadwal"].get("senin", [])
    output = format_jadwal_hari("senin", senin_list)
    assert "Senin" in output, "Format jadwal senin tidak sesuai!"
    print("[OK] Logika jadwal & rutinitas terverifikasi.")

def test_tugas_crud():
    """Memverifikasi operasi simpan dan baca tugas (dengan jam dan tanpa jam)"""
    sample_tugas = [
        {
            "id": 1,
            "nama_tugas": "Tugas Dengan Jam",
            "deadline": "20-08-2026",
            "jam": "23:59",
            "matkul": "Keamanan Jaringan",
            "dibuat_pada": "2026-08-15 07:00:00"
        },
        {
            "id": 2,
            "nama_tugas": "Tugas Tanpa Jam",
            "deadline": "22-08-2026",
            "jam": "-",
            "matkul": "Sistem Operasi",
            "dibuat_pada": "2026-08-15 07:00:00"
        }
    ]
    assert save_tugas_data(sample_tugas), "Gagal menyimpan sample tugas!"
    loaded = load_tugas_data()
    assert len(loaded) == 2, "Jumlah tugas yang dimuat tidak sesuai!"
    assert loaded[0]["jam"] == "23:59", "Data jam tugas 1 tidak cocok!"
    assert loaded[1]["jam"] == "-", "Data jam tugas 2 tidak cocok!"
    print("[OK] Logika tugas (tugas.json) dengan fitur jam terverifikasi.")

def test_todo_crud():
    """Memverifikasi operasi simpan, baca, normalisasi hari, dan multi-ID to-do spontan"""
    from utils import parse_hari_todo
    from datetime import datetime
    
    # 1. Verifikasi parse_hari_todo
    dummy_senin = datetime(2026, 9, 7)  # 7 Sept 2026 adalah Senin (weekday 0)
    assert parse_hari_todo("senin") == "senin"
    assert parse_hari_todo("Hari Kamis") == "kamis"
    assert parse_hari_todo("setiap hari") == "setiap hari"
    assert parse_hari_todo("tiap hari") == "setiap hari"
    assert parse_hari_todo("hari ini", dummy_senin) == "senin"
    assert parse_hari_todo("besok", dummy_senin) == "selasa"
    assert parse_hari_todo("bukan_hari") is None

    # 2. Simpan dan muat data to-do dengan hari dan tanpa hari (backward compatibility)
    sample_todo = [
        {
            "id": 1,
            "kegiatan": "Ambil laundry sore ini",
            "dibuat_pada": "2026-08-17 07:00:00"
        },
        {
            "id": 2,
            "kegiatan": "Servis motor ke bengkel",
            "hari": "kamis",
            "dibuat_pada": "2026-09-06 10:00:00"
        },
        {
            "id": 3,
            "kegiatan": "Olahraga pagi",
            "hari": "setiap hari",
            "dibuat_pada": "2026-09-06 10:00:00"
        }
    ]
    assert save_todo_data(sample_todo), "Gagal menyimpan sample to-do!"
    loaded = load_todo_data()
    assert len(loaded) == 3, "Jumlah to-do yang dimuat tidak sesuai!"
    assert loaded[0].get("hari", "hari ini") == "hari ini", "Fallback backward compatibility gagal!"
    assert loaded[1]["hari"] == "kamis", "Hari to-do spesifik tidak tersimpan!"
    assert loaded[2]["hari"] == "setiap hari", "Hari to-do berulang tidak tersimpan!"

    # 3. Filter to-do untuk hari Kamis
    todo_kamis = [
        t for t in loaded
        if t.get("hari", "hari ini").lower() in ("kamis", "setiap hari", "semua")
    ]
    assert len(todo_kamis) == 2  # Servis motor (kamis) + Olahraga (setiap hari)

    # 4. Multi-ID berestodo simulasi
    target_ids = [1, 3]
    sisa = [t for t in loaded if t["id"] not in target_ids]
    assert len(sisa) == 1 and sisa[0]["id"] == 2

    # Bersihkan file pengujian
    save_todo_data([])
    print("[OK] Logika to-do spontan (input hari, filter, & multi-ID) terverifikasi.")

def test_agenda_crud():
    """Memverifikasi operasi simpan, baca, konversi tanggal fleksibel, dan multi-ID agenda"""
    from utils import parse_deadline_input

    # 1. Pastikan parsing input fleksibel menghasilkan format standar dd-mm-yyyy
    tgl_teks, _ = parse_deadline_input("15 september 2026")
    assert tgl_teks == "15-09-2026"

    tgl_besok, _ = parse_deadline_input("besok")
    assert tgl_besok is not None

    sample_agenda = [
        {
            "id": 1,
            "nama_acara": "Rapat Kerja Ormawa",
            "tanggal": "22-08-2026",
            "keterangan": "16:00 di Gedung B",
            "dibuat_pada": "2026-08-18 19:00:00"
        },
        {
            "id": 2,
            "nama_acara": "Workshop IoT",
            "tanggal": tgl_teks,
            "keterangan": "Pukul 09:00 WIB",
            "dibuat_pada": "2026-09-06 10:00:00"
        },
        {
            "id": 3,
            "nama_acara": "Evaluasi",
            "tanggal": tgl_besok,
            "keterangan": "Zoom Meeting",
            "dibuat_pada": "2026-09-06 10:00:00"
        }
    ]
    assert save_agenda_data(sample_agenda), "Gagal menyimpan sample agenda!"
    loaded = load_agenda_data()
    assert len(loaded) == 3, "Jumlah agenda yang dimuat tidak sesuai!"
    assert loaded[1]["tanggal"] == "15-09-2026"

    # Multi-ID simulasi hapus agenda
    target_ids = [1, 3]
    sisa = [a for a in loaded if a["id"] not in target_ids]
    assert len(sisa) == 1 and sisa[0]["id"] == 2

    # Bersihkan file pengujian
    save_agenda_data([])
    print("[OK] Logika agenda (agenda.json, parsing fleksibel, & multi-ID) terverifikasi.")

def test_deadline_format_validation():
    """Memastikan tanggal deadline harus menggunakan format dd-mm-yyyy dan jam hh:mm"""
    assert is_valid_deadline("20-08-2026") is True
    assert is_valid_deadline("20-08-2026 23:59") is True
    assert is_valid_deadline("20-08-2026 25:00") is False
    assert is_valid_deadline("2026-08-20") is False
    assert is_valid_deadline("32-08-2026") is False
    assert is_valid_deadline("20/08/2026") is False
    assert is_valid_time("23:59") is True
    assert is_valid_time("23.59") is True
    assert is_valid_time("9:00") is True
    # Format teks nama bulan fleksibel & urutan acak
    assert is_valid_deadline("12 september 2026") is True
    assert is_valid_deadline("2026 september 12") is True
    assert is_valid_deadline("september 12 2026") is True
    assert is_valid_deadline("12 sep 2026 23:59") is True
    # Format hari relatif & spesifik
    assert is_valid_deadline("hari ini") is True
    assert is_valid_deadline("besok") is True
    assert is_valid_deadline("lusa") is True
    assert is_valid_deadline("jumat") is True
    assert is_valid_deadline("hari senin") is True
    assert is_valid_deadline("besok 15:00") is True

    from utils import parse_deadline_input
    from datetime import timedelta
    from config import get_now_wib

    d1, t1 = parse_deadline_input("12 september 2026")
    assert d1 == "12-09-2026" and t1 is None

    d2, t2 = parse_deadline_input("2026 september 12 23:59")
    assert d2 == "12-09-2026" and t2 == "23:59"

    d3, t3 = parse_deadline_input("september 12 2026")
    assert d3 == "12-09-2026" and t3 is None

    d_besok, t_besok = parse_deadline_input("besok 15:00")
    assert t_besok == "15:00"
    assert d_besok == (get_now_wib() + timedelta(days=1)).strftime("%d-%m-%Y")

    print("[OK] Validasi format deadline (angka & teks fleksibel) & jam terverifikasi.")

def test_daily_briefing():
    """Memverifikasi perangkaian pesan briefing harian otomatis"""
    from config import HARI_INDONESIA, get_now_wib
    now_dt = get_now_wib()
    hari_ini = HARI_INDONESIA[now_dt.weekday()]
    hari_lain = HARI_INDONESIA[(now_dt.weekday() + 2) % 7]

    # Uji filtering to-do di daily briefing
    test_todo = [
        {"id": 101, "kegiatan": "To-Do Khusus Hari Ini", "hari": hari_ini},
        {"id": 102, "kegiatan": "To-Do Hari Lain", "hari": hari_lain}
    ]
    save_todo_data(test_todo)
    briefing = generate_daily_briefing()
    assert "PENGINGAT HARIAN" in briefing, "Header pengingat harian tidak ditemukan!"
    assert "To-Do Khusus Hari Ini" in briefing, "To-do hari ini harus masuk briefing!"
    assert "To-Do Hari Lain" not in briefing, "To-do hari lain tidak boleh masuk briefing hari ini!"
    save_todo_data([])
    print("[OK] Logika perangkaian pesan briefing harian & filter to-do terverifikasi.")

def test_subscribers():
    """Memverifikasi pencatatan subscriber chat id"""
    dummy_chat_id = 99887766
    register_subscriber(dummy_chat_id)
    subs = load_subscribers()
    assert dummy_chat_id in subs, "Chat ID tidak berhasil didaftarkan!"
    subs.remove(dummy_chat_id)
    import json
    from bot import CONFIG_FILE
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"subscribers": subs}, f, indent=2)
    print("[OK] Logika pendaftaran chat ID (subscriber) terverifikasi.")

def test_task_reminder_logic():
    """Memverifikasi logika perhitungan deadline & filter < 6 jam tugas"""
    from bot import get_task_deadline_dt, should_remind_task

    # 1. Tugas dibuat 1 jam sebelum deadline (Mepet < 6 jam) -> False (tidak diingatkan)
    tugas_mepet = {
        "id": 101,
        "nama_tugas": "Tugas Mepet",
        "deadline": "10-09-2026",
        "jam": "15:00",
        "dibuat_pada": "2026-09-10 14:00:00"
    }
    assert should_remind_task(tugas_mepet) is False, "Tugas mepet < 6 jam harusnya diabaikan dari pengingat!"

    # 2. Tugas dibuat 2 hari sebelum deadline (>= 6 jam) -> True (diingatkan)
    tugas_normal = {
        "id": 102,
        "nama_tugas": "Tugas Normal",
        "deadline": "10-09-2026",
        "jam": "23:59",
        "dibuat_pada": "2026-09-08 10:00:00"
    }
    assert should_remind_task(tugas_normal) is True, "Tugas normal >= 6 jam harusnya diingatkan!"

    # 3. Verifikasi perhitungan datetime deadline
    dt = get_task_deadline_dt(tugas_normal)
    assert dt is not None
    assert dt.hour == 23 and dt.minute == 59
    print("[OK] Logika filter pengingat tugas (aturan < 6 jam & datetime) terverifikasi.")

def test_rutinitas_crud():
    """Memverifikasi logika penyeragaman dan filtering hari pada rutinitas"""
    # 1. Penyeragaman data teks format lama vs objek baru
    old_str = "07:30 - Senam Pagi"
    norm1 = normalize_rutinitas_item(old_str, 5)
    assert norm1["id"] == 5
    assert norm1["hari"] == "setiap hari"
    assert norm1["jam"] == "07:30"
    assert norm1["kegiatan"] == "Senam Pagi"

    # 2. Objek baru dengan hari spesifik
    new_obj = {"id": 10, "hari": "jumat", "jam": "11:30", "kegiatan": "Salat Jumat"}
    norm2 = normalize_rutinitas_item(new_obj, 10)
    assert norm2["hari"] == "jumat"
    assert norm2["jam"] == "11:30"

    # 3. Pengujian parsing input multi-hari (parse_hari_rutinitas)
    assert parse_hari_rutinitas("senin, kamis") == "senin, kamis"
    assert parse_hari_rutinitas("kamis, senin") == "senin, kamis"  # Terurut
    assert parse_hari_rutinitas("selasa & jumat") == "selasa, jumat"
    assert parse_hari_rutinitas("senin dan rabu") == "senin, rabu"
    assert parse_hari_rutinitas("hari rabu, hari sabtu") == "rabu, sabtu"
    assert parse_hari_rutinitas("setiap hari") == "setiap hari"
    assert parse_hari_rutinitas("bukan_hari") is None

    # 4. Pengujian filter hari aktif (is_rutinitas_active_on_day)
    assert is_rutinitas_active_on_day("setiap hari", "senin") is True
    assert is_rutinitas_active_on_day("senin, kamis", "senin") is True
    assert is_rutinitas_active_on_day("senin, kamis", "kamis") is True
    assert is_rutinitas_active_on_day("senin, kamis", "selasa") is False
    assert is_rutinitas_active_on_day("jumat", "jumat") is True
    assert is_rutinitas_active_on_day("jumat", "minggu") is False

    # 5. Simulasi pencopotan hari dari rutinitas (hari tertentu)
    # Skenario A: Rutinitas 'senin, jumat', hapus 'jumat' -> sisa 'senin'
    days_item = [d.strip() for d in "senin, jumat".split(",")]
    days_item.remove("jumat")
    assert ", ".join(days_item) == "senin"

    # Skenario B: Rutinitas 'setiap hari', hapus 'minggu' -> sisa 6 hari
    from utils import ORDER_HARI
    active_all = list(ORDER_HARI)
    active_all.remove("minggu")
    assert len(active_all) == 6
    assert "minggu" not in active_all

    # Skenario C: Rutinitas 'jumat', hapus 'jumat' -> sisa 0 (dihapus permanen)
    single_day = ["jumat"]
    single_day.remove("jumat")
    assert len(single_day) == 0

    # 6. Simulasi filter hari aktif dalam list rutinitas
    semua_rutinitas = [
        {"id": 1, "hari": "setiap hari", "jam": "04:30", "kegiatan": "Subuh"},
        {"id": 2, "hari": "senin, jumat", "jam": "11:30", "kegiatan": "Salat / Senam"},
        {"id": 3, "hari": "minggu", "jam": "08:00", "kegiatan": "Olahraga"}
    ]
    hari_jumat_aktif = [
        r for r in semua_rutinitas 
        if is_rutinitas_active_on_day(r["hari"], "jumat")
    ]
    assert len(hari_jumat_aktif) == 2  # Subuh + Salat / Senam

    # 7. Simulasi input multi-ID dengan urutan acak & pemisah koma/spasi
    input_str = "4, 1, 3 2 1"
    raw_tokens = input_str.replace(",", " ").split()
    parsed_ids = list(dict.fromkeys([int(t) for t in raw_tokens if t.isdigit()]))
    assert parsed_ids == [4, 1, 3, 2]  # Duplikat '1' di akhir hilang, urutan acak diterima

    print("[OK] Logika penyeragaman, multi-hari, filter hari, & pencopotan hari rutinitas terverifikasi.")

def test_cleanup_expired_tasks():
    """Memverifikasi penghapusan otomatis tugas yang telah melewati deadline."""
    from datetime import datetime
    from config import WIB

    # Mock waktu acuan: 11 September 2026, 10:00 WIB
    mock_now = datetime(2026, 9, 11, 10, 0, tzinfo=WIB)

    sample_tugas = [
        {
            "id": 1,
            "nama_tugas": "Tugas Sudah Lewat Kemarin",
            "deadline": "10-09-2026",
            "jam": "23:59",
            "matkul": "Kalkulus"
        },
        {
            "id": 2,
            "nama_tugas": "Tugas Hari Ini Jam Sudah Lewat",
            "deadline": "11-09-2026",
            "jam": "08:00",
            "matkul": "Fisika"
        },
        {
            "id": 3,
            "nama_tugas": "Tugas Hari Ini Jam Belum Lewat",
            "deadline": "11-09-2026",
            "jam": "14:00",
            "matkul": "Pemrograman"
        },
        {
            "id": 4,
            "nama_tugas": "Tugas Masa Depan",
            "deadline": "15-09-2026",
            "jam": "23:59",
            "matkul": "Basis Data"
        }
    ]

    save_tugas_data(sample_tugas)
    aktif = cleanup_expired_tasks(mock_now)

    assert len(aktif) == 2, f"Harusnya tersisa 2 tugas aktif, tetapi ada {len(aktif)}!"
    aktif_ids = {t["id"] for t in aktif}
    assert 3 in aktif_ids, "Tugas ID 3 (belum lewat) harusnya tetap ada!"
    assert 4 in aktif_ids, "Tugas ID 4 (masa depan) harusnya tetap ada!"
    assert 1 not in aktif_ids, "Tugas ID 1 (kemarin) harusnya terhapus!"
    assert 2 not in aktif_ids, "Tugas ID 2 (tadi pagi) harusnya terhapus!"

    # Pastikan data di file tugas.json juga terupdate
    loaded = load_tugas_data()
    assert len(loaded) == 2, "Data di storage tugas.json tidak terupdate setelah cleanup!"

    # Bersihkan file setelah pengujian
    save_tugas_data([])
    print("[OK] Logika penghapusan otomatis tugas kedaluwarsa (cleanup_expired_tasks) terverifikasi.")

def test_rutinitas_smart_features():
    """
    Memverifikasi 4 fitur pintar rutinitas:
    1. ID berurutan kronologis berdasarkan jam.
    2. Auto-merge kegiatan yang sama di jam yang sama.
    3. Auto-reindex saat ada rutinitas yang dihapus.
    4. Deteksi tabrakan jadwal (conflict detection).
    """
    # 1. Uji ID berurutan kronologis berdasarkan jam
    acak = [
        {"id": 99, "hari": "senin", "jam": "19:00", "kegiatan": "Malam"},
        {"id": 50, "hari": "setiap hari", "jam": "04:30", "kegiatan": "Pagi Buta"},
        {"id": 12, "hari": "rabu", "jam": "07:00", "kegiatan": "Sarapan"},
    ]
    terurut = reindex_rutinitas(acak)
    assert [r["id"] for r in terurut] == [1, 2, 3]
    assert [r["jam"] for r in terurut] == ["04:30", "07:00", "19:00"]
    assert terurut[0]["kegiatan"] == "Pagi Buta"

    # 2. Uji Auto-Merge kegiatan & jam yang sama
    hari_awal = "senin, selasa, rabu, kamis, jumat"
    hari_tambah = "sabtu, minggu"
    merged = merge_rutinitas_days(hari_awal, hari_tambah)
    assert merged == "setiap hari"

    hari_parsial = merge_rutinitas_days("senin", "kamis")
    assert hari_parsial == "senin, kamis"

    # 3. Uji Deteksi Tabrakan Jadwal (Conflict Detection)
    jadwal_ada = [
        {"id": 1, "hari": "senin, kamis", "jam": "06:00", "kegiatan": "Kemas rumah"},
        {"id": 2, "hari": "jumat", "jam": "11:30", "kegiatan": "Jumatan"},
    ]
    # Skenario A: Bentrok di hari Senin pada jam 06:00
    conflict_1 = find_rutinitas_conflict(jadwal_ada, "06:00", "senin")
    assert conflict_1 is not None
    item_bentrok, hari_bentrok = conflict_1
    assert item_bentrok["id"] == 1
    assert "senin" in hari_bentrok

    # Skenario B: Tidak bentrok (jam 06:00 tapi hari Selasa, padahal ID 1 cuma Senin & Kamis)
    conflict_2 = find_rutinitas_conflict(jadwal_ada, "06:00", "selasa")
    assert conflict_2 is None

    # Skenario C: Tidak bentrok (jam beda)
    conflict_3 = find_rutinitas_conflict(jadwal_ada, "07:00", "senin")
    assert conflict_3 is None

    # 4. Uji Auto-Reindex saat ada rutinitas yang dihapus
    sebelum_hapus = [
        {"id": 1, "jam": "04:30", "kegiatan": "A"},
        {"id": 2, "jam": "06:00", "kegiatan": "B"},
        {"id": 3, "jam": "08:00", "kegiatan": "C"},
        {"id": 4, "jam": "12:00", "kegiatan": "D"},
    ]
    sisa = [r for r in sebelum_hapus if r["id"] != 2]
    sisa_reindexed = reindex_rutinitas(sisa)
    assert len(sisa_reindexed) == 3
    assert [r["id"] for r in sisa_reindexed] == [1, 2, 3]
    assert sisa_reindexed[1]["kegiatan"] == "C"

    print("[OK] 4 Fitur pintar rutinitas (reindex kronologis, auto-merge, conflict detection, auto-reindex hapus) terverifikasi.")

if __name__ == "__main__":
    test_handlers()
    test_jadwal_data()
    test_rutinitas_crud()
    test_rutinitas_smart_features()
    test_tugas_crud()
    test_cleanup_expired_tasks()
    test_todo_crud()
    test_agenda_crud()
    test_deadline_format_validation()
    test_task_reminder_logic()
    test_daily_briefing()
    test_subscribers()
    print("[OK] Seluruh self-check pengujian berhasil!")
