from flask import Flask, request, jsonify, render_template
import mysql.connector
import datetime
import traceback

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1590",
        database="hospital_db"
    )

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/admin')
def admin():
    return render_template("admin.html")


@app.route('/districts')
def districts():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, address FROM districts")
    data = cur.fetchall()
    conn.close()
    return jsonify(data)


@app.route('/doctors/<int:district_id>')
def doctors(district_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, full_name, specialization, cabinet
        FROM doctors
        WHERE district_id=%s
    """, (district_id,))
    data = cur.fetchall()
    conn.close()
    return jsonify(data)


@app.route('/available/<int:doctor_id>/<date>')
def available(doctor_id, date):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    slots = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]

    cur.execute("""
        SELECT time FROM appointments
        WHERE doctor_id=%s AND date=%s
    """, (doctor_id, date))

    busy = [str(x["time"])[:5] for x in cur.fetchall()]
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
        cur = conn.cursor(dictionary=True)

        day = datetime.datetime.strptime(data['date'], "%Y-%m-%d").weekday()
        if day >= 5:
            return "Только будни"

        cur.execute("""
            SELECT id FROM appointments
            WHERE doctor_id=%s AND date=%s AND time=%s
        """, (data['doctor_id'], data['date'], data['time']))

        if cur.fetchone():
            return "Это время уже занято"

        cur.execute("SELECT id FROM patients WHERE iin=%s", (data['iin'],))
        patient = cur.fetchone()

        if patient:
            patient_id = patient['id']
        else:
            cur.execute("""
                INSERT INTO patients (full_name, iin, phone, gender)
                VALUES (%s,%s,%s,%s)
            """, (
                data['name'],
                data['iin'],
                data.get('phone', ''),
                data.get('gender', '')
            ))
            patient_id = cur.lastrowid

        cur.execute("""
            INSERT INTO appointments (doctor_id, patient_id, date, time)
            VALUES (%s,%s,%s,%s)
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
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT a.id,
               d.full_name AS doctor,
               d.specialization,
               d.cabinet,
               p.id AS patient_id,
               p.full_name AS patient,
               p.iin,
               p.phone,
               a.date,
               a.time
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN patients p ON a.patient_id = p.id
    """)

    data = cur.fetchall()
    conn.close()
    return jsonify(data)


@app.route('/patients')
def patients():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, full_name, iin FROM patients")
    data = cur.fetchall()
    conn.close()
    return jsonify(data)


@app.route('/add_record', methods=['POST'])
def add_record():
    data = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO medical_records (doctor_id, patient_id, diagnosis)
        VALUES (%s,%s,%s)
    """, (data['doctor_id'], data['patient_id'], data['diagnosis']))

    conn.commit()
    conn.close()

    return "OK"


@app.route('/records_by_iin/<iin>')
def records_by_iin(iin):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT d.full_name AS doctor, m.diagnosis
        FROM medical_records m
        JOIN doctors d ON m.doctor_id = d.id
        JOIN patients p ON m.patient_id = p.id
        WHERE p.iin=%s
    """, (iin,))

    data = cur.fetchall()
    conn.close()
    return jsonify(data)

if __name__ == "__main__":
    app.run()