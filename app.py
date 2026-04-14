from flask import Flask, request, jsonify, render_template
import sqlite3
import datetime
import os

app = Flask(__name__)

DB_NAME = "hospital.db"


# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- INIT DB ----------------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS districts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        specialization TEXT,
        cabinet TEXT,
        district_id INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        iin TEXT,
        phone TEXT,
        gender TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        date TEXT,
        time TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        diagnosis TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- INIT ON START ----------------
if not os.path.exists(DB_NAME):
    init_db()


# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/admin')
def admin():
    return render_template("admin.html")


@app.route('/districts')
def districts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM districts")
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/doctors/<int:district_id>')
def doctors(district_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM doctors WHERE district_id=?", (district_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/available/<int:doctor_id>/<date>')
def available(doctor_id, date):

    slots = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT time FROM appointments
        WHERE doctor_id=? AND date=?
    """, (doctor_id, date))

    busy = [r[0] for r in cur.fetchall()]
    conn.close()

    free = [t for t in slots if t not in busy]
    return jsonify(free)


@app.route('/add', methods=['POST'])
def add():
    data = request.json

    conn = get_db()
    cur = conn.cursor()

    # проверка занято
    cur.execute("""
        SELECT * FROM appointments
        WHERE doctor_id=? AND date=? AND time=?
    """, (data['doctor_id'], data['date'], data['time']))

    if cur.fetchone():
        return "BUSY"

    # пациент
    cur.execute("SELECT id FROM patients WHERE iin=?", (data['iin'],))
    p = cur.fetchone()

    if p:
        patient_id = p[0]
    else:
        cur.execute("""
            INSERT INTO patients (full_name, iin, phone, gender)
            VALUES (?,?,?,?)
        """, (data['name'], data['iin'], data['phone'], data['gender']))
        patient_id = cur.lastrowid

    # запись
    cur.execute("""
        INSERT INTO appointments (doctor_id, patient_id, date, time)
        VALUES (?,?,?,?)
    """, (data['doctor_id'], patient_id, data['date'], data['time']))

    conn.commit()
    conn.close()

    return "OK"


@app.route('/all_appointments')
def all_appointments():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id,
               d.full_name,
               d.specialization,
               d.cabinet,
               p.id,
               p.full_name,
               p.iin,
               p.phone,
               a.date,
               a.time
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN patients p ON a.patient_id = p.id
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify(rows)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
