from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ganti-secret-key-untuk-produksi")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puskesmas.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_column_if_missing(conn, table, column, definition):
    """Tambahkan kolom tanpa menghapus atau membuat ulang data lama."""
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return True
    return False


def init_db():
    con = db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            profession TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            provider_id INTEGER,
            service TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'Menunggu',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS immunizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age_group TEXT NOT NULL,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            provider_id INTEGER,
            title TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # MIGRASI DATABASE LAMA:
    # CREATE TABLE IF NOT EXISTS tidak menambahkan kolom ke tabel yang sudah ada.
    # Karena itu, tambahkan kolom yang mungkin belum ada pada database lama.
    add_column_if_missing(con, "users", "phone", "TEXT DEFAULT ''")
    add_column_if_missing(con, "users", "address", "TEXT DEFAULT ''")
    add_column_if_missing(con, "users", "profession", "TEXT DEFAULT ''")
    users_created_added = add_column_if_missing(con, "users", "created_at", "TEXT")

    add_column_if_missing(con, "appointments", "provider_id", "INTEGER")
    add_column_if_missing(con, "appointments", "notes", "TEXT DEFAULT ''")
    add_column_if_missing(con, "appointments", "status", "TEXT DEFAULT 'Menunggu'")
    appointment_created_added = add_column_if_missing(
        con, "appointments", "created_at", "TEXT"
    )

    add_column_if_missing(con, "health_records", "provider_id", "INTEGER")
    health_created_added = add_column_if_missing(
        con, "health_records", "created_at", "TEXT"
    )

    # Isi created_at untuk data lama agar query ORDER BY created_at tidak gagal.
    if users_created_added:
        con.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    if appointment_created_added:
        con.execute("""
            UPDATE appointments
            SET created_at = COALESCE(NULLIF(appointment_date, ''), CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR created_at = ''
        """)
    else:
        con.execute("""
            UPDATE appointments
            SET created_at = COALESCE(NULLIF(appointment_date, ''), CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR created_at = ''
        """)
    if health_created_added:
        con.execute("UPDATE health_records SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        seeds = [
            ("Administrator", "admin@puskesmas.test", "admin123", "admin", "081200000001", "Puskesmas Digital", "Administrator"),
            ("Dr. Andi Pratama", "dokter@puskesmas.test", "dokter123", "dokter", "081200000002", "Bekasi", "Dokter Umum"),
            ("Siti Rahma, A.Md.Keb", "medis@puskesmas.test", "medis123", "medis", "081200000003", "Bekasi", "Bidan"),
            ("Ny. Siti Nurhaliza", "pasien@puskesmas.test", "pasien123", "pasien", "081200000004", "Bekasi", "Pengguna"),
        ]
        for name, email, password, role, phone, address, profession in seeds:
            con.execute(
                """INSERT INTO users(name,email,password,role,phone,address,profession)
                   VALUES(?,?,?,?,?,?,?)""",
                (name, email, generate_password_hash(password), role, phone, address, profession),
            )

        items = [
            ("Hepatitis B (HB-0)", "Bayi baru lahir", "Diberikan untuk membantu melindungi bayi dari infeksi Hepatitis B.", "Segera setelah lahir, idealnya kurang dari 24 jam"),
            ("BCG dan Polio Tetes 1", "Bayi usia 0–1 bulan", "Imunisasi dasar untuk perlindungan terhadap tuberkulosis berat dan polio.", "Usia 1 bulan"),
            ("DPT-HB-Hib 1 dan Polio 2", "Bayi usia 2 bulan", "Perlindungan terhadap difteri, pertusis, tetanus, Hepatitis B, Hib, dan polio.", "Usia 2 bulan"),
            ("Campak-Rubella (MR)", "Bayi usia 9 bulan", "Perlindungan terhadap penyakit campak dan rubella.", "Usia 9 bulan"),
            ("Imunisasi lanjutan", "Balita", "Jadwal lanjutan mengikuti program dan ketentuan fasilitas kesehatan.", "Sesuai buku KIA dan petugas"),
        ]
        con.executemany(
            "INSERT INTO immunizations(name,age_group,description,schedule) VALUES(?,?,?,?)",
            items,
        )
        # Data contoh hanya dimasukkan saat database benar-benar masih kosong.
        con.execute(
            """INSERT INTO appointments
               (patient_id,provider_id,service,appointment_date,notes,status)
               VALUES(1,2,'Konsultasi Dokter','2026-11-20T09:00','Pemeriksaan umum','Menunggu')"""
        )

    con.commit()
    con.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("Anda tidak memiliki akses ke halaman tersebut.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco


def current_user():
    if "user_id" not in session:
        return None
    con = db()
    user = con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    con.close()
    return user


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        con = db()
        user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        con.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Email atau password tidak sesuai.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    con = db()
    role = session["role"]
    if role == "admin":
        stats = {
            "users": con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "patients": con.execute("SELECT COUNT(*) FROM users WHERE role='pasien'").fetchone()[0],
            "providers": con.execute("SELECT COUNT(*) FROM users WHERE role IN ('dokter','medis')").fetchone()[0],
            "appointments": con.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
        }
        appointments = con.execute(
            """SELECT a.*, u.name AS patient FROM appointments a
               JOIN users u ON a.patient_id=u.id
               ORDER BY a.appointment_date DESC LIMIT 6"""
        ).fetchall()
    elif role in ("dokter", "medis"):
        stats = {
            "appointments": con.execute("SELECT COUNT(*) FROM appointments WHERE provider_id=?", (session["user_id"],)).fetchone()[0],
            "pending": con.execute("SELECT COUNT(*) FROM appointments WHERE provider_id=? AND status='Menunggu'", (session["user_id"],)).fetchone()[0],
            "patients": con.execute("SELECT COUNT(DISTINCT patient_id) FROM appointments WHERE provider_id=?", (session["user_id"],)).fetchone()[0],
        }
        appointments = con.execute(
            """SELECT a.*, u.name AS patient FROM appointments a
               JOIN users u ON a.patient_id=u.id
               WHERE a.provider_id=? ORDER BY a.appointment_date DESC LIMIT 8""",
            (session["user_id"],),
        ).fetchall()
    else:
        stats = {
            "appointments": con.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=?", (session["user_id"],)).fetchone()[0],
            "pending": con.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=? AND status='Menunggu'", (session["user_id"],)).fetchone()[0],
            "records": con.execute("SELECT COUNT(*) FROM health_records WHERE patient_id=?", (session["user_id"],)).fetchone()[0],
        }
        appointments = con.execute(
            """SELECT a.*, u.name AS provider FROM appointments a
               LEFT JOIN users u ON a.provider_id=u.id
               WHERE a.patient_id=? ORDER BY a.appointment_date DESC LIMIT 6""",
            (session["user_id"],),
        ).fetchall()
    con.close()
    return render_template("dashboard.html", stats=stats, appointments=appointments)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    con = db()
    if request.method == "POST":
        con.execute(
            "UPDATE users SET name=?,phone=?,address=?,profession=? WHERE id=?",
            (request.form["name"], request.form.get("phone", ""), request.form.get("address", ""), request.form.get("profession", ""), session["user_id"]),
        )
        con.commit()
        session["name"] = request.form["name"]
        flash("Profil berhasil diperbarui.", "success")
    user = con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    con.close()
    return render_template("profile.html", user=user)


@app.route("/imunisasi")
@login_required
def imunisasi():
    con = db()
    items = con.execute("SELECT * FROM immunizations ORDER BY id").fetchall()
    con.close()
    return render_template("imunisasi.html", items=items)


@app.route("/konsultasi", methods=["GET", "POST"])
@login_required
def konsultasi():
    con = db()
    if request.method == "POST":
        if session.get("role") != "pasien":
            con.close()
            flash("Hanya pasien yang dapat membuat permintaan konsultasi.", "error")
            return redirect(url_for("konsultasi"))
        provider_id = request.form.get("provider_id") or None
        con.execute(
            """INSERT INTO appointments(patient_id,provider_id,service,appointment_date,notes)
               VALUES(?,?,?,?,?)""",
            (session["user_id"], provider_id, request.form["service"], request.form["appointment_date"], request.form.get("notes", "")),
        )
        con.commit()
        flash("Permintaan konsultasi berhasil dikirim.", "success")
        con.close()
        return redirect(url_for("konsultasi"))

    providers = con.execute(
        "SELECT id,name,profession,role FROM users WHERE role IN ('dokter','medis') ORDER BY role"
    ).fetchall()
    if session["role"] == "pasien":
        appointments = con.execute(
            """SELECT a.*, u.name AS provider FROM appointments a
               LEFT JOIN users u ON a.provider_id=u.id
               WHERE a.patient_id=? ORDER BY a.created_at DESC""",
            (session["user_id"],),
        ).fetchall()
    elif session["role"] in ("dokter", "medis"):
        appointments = con.execute(
            """SELECT a.*, u.name AS patient FROM appointments a
               JOIN users u ON a.patient_id=u.id
               WHERE a.provider_id=? ORDER BY a.created_at DESC""",
            (session["user_id"],),
        ).fetchall()
    else:
        appointments = con.execute(
            """SELECT a.*, u.name AS patient FROM appointments a
               JOIN users u ON a.patient_id=u.id ORDER BY a.created_at DESC"""
        ).fetchall()
    con.close()
    return render_template("konsultasi.html", providers=providers, appointments=appointments)


@app.route("/appointment/<int:appointment_id>/status", methods=["POST"])
@roles_required("admin", "dokter", "medis")
def update_appointment(appointment_id):
    status = request.form.get("status")
    if status not in ("Menunggu", "Dikonfirmasi", "Selesai", "Dibatalkan"):
        flash("Status tidak valid.", "error")
    else:
        con = db()
        if session["role"] == "admin":
            con.execute("UPDATE appointments SET status=? WHERE id=?", (status, appointment_id))
        else:
            con.execute(
                "UPDATE appointments SET status=? WHERE id=? AND provider_id=?",
                (status, appointment_id, session["user_id"]),
            )
        con.commit()
        con.close()
        flash("Status konsultasi diperbarui.", "success")
    return redirect(url_for("konsultasi"))


@app.route("/pasien")
@roles_required("admin", "dokter", "medis")
def pasien():
    con = db()
    users = con.execute("SELECT * FROM users WHERE role='pasien' ORDER BY name").fetchall()
    con.close()
    return render_template("pasien.html", users=users)


@app.route("/pengguna", methods=["GET", "POST"])
@roles_required("admin")
def pengguna():
    con = db()
    if request.method == "POST":
        try:
            con.execute(
                """INSERT INTO users(name,email,password,role,phone,profession)
                   VALUES(?,?,?,?,?,?)""",
                (request.form["name"], request.form["email"].lower(), generate_password_hash(request.form["password"]), request.form["role"], request.form.get("phone", ""), request.form.get("profession", "")),
            )
            con.commit()
            flash("Pengguna baru berhasil ditambahkan.", "success")
        except sqlite3.IntegrityError:
            flash("Email sudah digunakan.", "error")
    users = con.execute("SELECT id,name,email,role,phone,profession FROM users ORDER BY role,name").fetchall()
    con.close()
    return render_template("pengguna.html", users=users)


@app.route("/rekam-medis", methods=["GET", "POST"])
@login_required
def rekam_medis():
    con = db()
    if request.method == "POST" and session["role"] in ("admin", "dokter", "medis"):
        con.execute(
            "INSERT INTO health_records(patient_id,provider_id,title,notes) VALUES(?,?,?,?)",
            (request.form["patient_id"], session["user_id"], request.form["title"], request.form["notes"]),
        )
        con.commit()
        flash("Catatan rekam medis tersimpan.", "success")
    if session["role"] == "pasien":
        records = con.execute(
            """SELECT h.*, u.name AS provider FROM health_records h
               LEFT JOIN users u ON h.provider_id=u.id
               WHERE h.patient_id=? ORDER BY h.created_at DESC""",
            (session["user_id"],),
        ).fetchall()
        patients = []
    else:
        records = con.execute(
            """SELECT h.*, p.name AS patient, u.name AS provider FROM health_records h
               JOIN users p ON h.patient_id=p.id
               LEFT JOIN users u ON h.provider_id=u.id
               ORDER BY h.created_at DESC"""
        ).fetchall()
        patients = con.execute("SELECT id,name FROM users WHERE role='pasien' ORDER BY name").fetchall()
    con.close()
    return render_template("rekam_medis.html", records=records, patients=patients)


@app.route("/ai")
@login_required
def ai():
    return render_template("ai.html")


@app.route("/api/ai", methods=["POST"])
@login_required
def ai_answer():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(answer="Silakan tuliskan pertanyaan terlebih dahulu."), 400
    if len(question) > 1500:
        return jsonify(error="Pertanyaan maksimal 1500 karakter."), 400

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            prompt = f"""Kamu adalah asisten informasi Puskesmas Digital. Jawab dalam bahasa Indonesia yang sederhana dan sopan. Berikan edukasi kesehatan umum dan informasi layanan saja. Jangan mendiagnosis, meresepkan obat, menentukan dosis, atau menggantikan dokter. Jika ada tanda darurat, sarankan segera mencari pertolongan medis. Jangan meminta NIK atau data pribadi sensitif. Pertanyaan: {question}"""
            response = client.models.generate_content(model=model, contents=prompt)
            return jsonify(answer=response.text or "Maaf, belum ada jawaban. Silakan coba kembali.")
        except Exception:
            app.logger.exception("Gemini API error")
            return jsonify(error="Layanan AI sedang mengalami gangguan. Periksa API Key dan koneksi, lalu coba kembali."), 502

    q = question.lower()
    if any(x in q for x in ("imunisasi", "vaksin")):
        answer = "Jadwal imunisasi bergantung pada usia dan riwayat imunisasi. Cocokkan dengan Buku KIA dan konfirmasikan jenis serta waktu pemberian kepada petugas Puskesmas."
    elif any(x in q for x in ("darurat", "sesak", "kejang", "pingsan")):
        answer = "Jika mengalami kondisi gawat darurat seperti sesak napas berat, kejang, atau penurunan kesadaran, segera cari pertolongan medis darurat atau kunjungi IGD terdekat."
    else:
        answer = "Ini adalah mode demo tanpa koneksi Gemini. Untuk jawaban AI langsung, isi GEMINI_API_KEY pada file .env dan instal dependensi google-genai. Untuk keluhan pribadi, silakan buat konsultasi dengan tenaga kesehatan."
    return jsonify(answer=answer)


@app.context_processor
def inject_date():
    return {"now_date": datetime.now().strftime("%d %B %Y")}


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
