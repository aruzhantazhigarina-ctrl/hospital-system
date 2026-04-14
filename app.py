from flask import Flask, request, jsonify, render_template
import sqlite3
import datetime
import traceback
import os

app = Flask(__name__)

DB = "hospital.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# 🔥 СОЗДАНИЕ БД (автоматически при запуске)
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS districts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT
    );

    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        specialization TEXT,
        cabinet TEXT,
        district_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        iin TEXT,
        phone TEXT,
        gender TEXT
    );

    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        date TEXT,
        time TEXT,
        UNIQUE (doctor_id, date, time)
    );

    CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        diagnosis TEXT
    );
    """)

    # 🔴 если пусто — заполняем
    cur.execute("SELECT COUNT(*) FROM districts")
    if cur.fetchone()[0] == 0:

        cur.executescript("""

        INSERT INTO districts (name, address) VALUES
        ('Есиль', 'Мангилик Ел 52'),
        ('Сарыарка', 'Тауелсиздик 1-25'),
        ('Алматы', 'Абая 10');

        INSERT INTO doctors (full_name, specialization, cabinet, district_id) VALUES

        ('Сериков Нурлан Ерланович', 'Стоматолог-терапевт', '101', 1),
        ('Касымов Айбек Нурланович', 'Хирург-стоматолог', '102', 1),
        ('Жумабеков Ержан Канатович', 'Челюстно-лицевой хирург', '103', 1),
        ('Тлеубергенов Данияр Русланович', 'Ортодонт', '104', 1),
        ('Алиева Жанар Болатовна', 'Гнатолог', '105', 1),
        ('Омаров Руслан Дастанович', 'Имплантолог', '106', 1),

        ('Бекетов Арман Серикович', 'Стоматолог-терапевт', '201', 2),
        ('Нурпеисов Канат Ермекович', 'Хирург-стоматолог', '202', 2),
        ('Садыков Марат Нурланович', 'Челюстно-лицевой хирург', '203', 2),
        ('Кенжебаева Алия Ерлановна', 'Ортодонт', '204', 2),
        ('Турсунов Ермек Болатович', 'Гнатолог', '205', 2),
        ('Жаксылыков Дастан Канатович', 'Имплантолог', '206', 2),

        ('Айдаров Тимур Ерланович', 'Стоматолог-терапевт', '301', 3),
        ('Смагулова Динара Нурлановна', 'Хирург-стоматолог', '302', 3),
        ('Исабеков Нурсултан Серикович', 'Челюстно-лицевой хирург', '303', 3),
        ('Калиева Айгуль Болатовна', 'Ортодонт', '304', 3),
        ('Мухамеджанов Олжас Ермекович', 'Гнатолог', '305', 3),
        ('Рахимов Ерасыл Нурланович', 'Имплантолог', '306', 3);
        """)

    conn.commit()
    conn.close()


# 🔥 ИНИЦИАЛИЗАЦИЯ
init_db()


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

    data = cur.execute("SELECT * FROM districts").fetchall()
    conn.close()

    return jsonify([dict(x) for x in data])


@app.route('/doctors/<int:district_id>')
def doctors(district_id):
    conn = get_db()
    cur = conn.cursor()

    data = cur.execute("""
        SELECT * FROM doctors WHERE district_id=?
    """, (district_id,)).fetchall()

    conn.close()
    return jsonify([dict(x) for x in data])


@app.route('/available/<int:doctor_id>/<date>')
def available(doctor_id, date):
    conn = get_db()
    cur = conn.cursor()

    slots = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]

    busy = cur.execute("""
        SELECT time FROM appointments
        WHERE doctor_id=? AND date=?
    """, (doctor_id, date)).fetchall()

    busy = [x["time"] for x in busy]

    free = [t for t in slots if t not in busy]

    conn.close()
    return jsonify(free)


@app.route('/add', methods=['POST'])
def add():
    try:
        data = request.json

        if not data.get('name'):
            return "Введите имя"
        if not data.get('iin'):
            return "Введите ИИН"
        if not data.get('date'):
            return "Выберите дату"
        if not data.get('time'):
            return "Выберите время"

        conn = get_db()
        cur = conn.cursor()

        day = datetime.datetime.strptime(data['date'], "%Y-%m-%d").weekday()
        if day >= 5:
            return "Только будни"

        # проверка занятости
        if cur.execute("""
            SELECT id FROM appointments
            WHERE doctor_id=? AND date=? AND time=?
        """, (data['doctor_id'], data['date'], data['time'])).fetchone():
            return "Это время уже занято"

        # пациент
        patient = cur.execute("SELECT id FROM patients WHERE iin=?", (data['iin'],)).fetchone()

        if patient:
            patient_id = patient["id"]
        else:
            cur.execute("""
                INSERT INTO patients (full_name, iin, phone, gender)
                VALUES (?,?,?,?)
            """, (
                data['name'],
                data['iin'],
                data.get('phone', ''),
                data.get('gender', '')
            ))
            patient_id = cur.lastrowid

        # запись
        cur.execute("""
            INSERT INTO appointments (doctor_id, patient_id, date, time)
            VALUES (?,?,?,?)
        """, (
            data['doctor_id'],
            patient_id,
            data['date'],
            data['time']
        ))

        conn.commit()
        conn.close()

        return "OK"

    except Exception as e:
        traceback.print_exc()
        return str(e)


@app.route('/all_appointments')
def all_appointments():
    conn = get_db()
    cur = conn.cursor()

    data = cur.execute("""
        SELECT a.id,
               d.full_name AS doctor,
               d.specialization,
               d.cabinet,
               p.full_name AS patient,
               p.iin,
               a.date,
               a.time
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN patients p ON a.patient_id = p.id
    """).fetchall()

    conn.close()
    return jsonify([dict(x) for x in data])


@app.route('/patients')
def patients():
    conn = get_db()
    cur = conn.cursor()

    data = cur.execute("SELECT id, full_name, iin FROM patients").fetchall()

    conn.close()
    return jsonify([dict(x) for x in data])


@app.route('/add_record', methods=['POST'])
def add_record():
    try:
        data = request.json

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO medical_records (doctor_id, patient_id, diagnosis)
            VALUES (?,?,?)
        """, (data['doctor_id'], data['patient_id'], data['diagnosis']))

        conn.commit()
        conn.close()

        return "OK"

    except Exception as e:
        traceback.print_exc()
        return str(e)


@app.route('/records_by_iin/<iin>')
def records_by_iin(iin):
    conn = get_db()
    cur = conn.cursor()

    data = cur.execute("""
        SELECT d.full_name AS doctor, m.diagnosis
        FROM medical_records m
        JOIN doctors d ON m.doctor_id = d.id
        JOIN patients p ON m.patient_id = p.id
        WHERE p.iin=?
    """, (iin,)).fetchall()

    conn.close()
    return jsonify([dict(x) for x in data])


if __name__ == "__main__":
    app.run()
@app.route('/delete_appointment/<int:id>', methods=['DELETE'])
def delete_appointment(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM appointments WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return "OK"
