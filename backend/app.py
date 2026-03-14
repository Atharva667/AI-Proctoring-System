from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask import send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime
import base64
import numpy as np
import cv2
from services.ai_proctoring import detect_faces
from werkzeug.security import generate_password_hash, check_password_hash

 
# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = "ai_proctoring_secret_key"
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "activity_log.txt")

@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():

    data = request.json['image']
    encoded = data.split(',')[1]

    img = base64.b64decode(encoded)
    npimg = np.frombuffer(img, dtype=np.uint8)

    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    faces = detect_faces(frame)

    return {"faces": faces}


# ---------------- DATABASE ----------------
def get_db():
    return mysql.connector.connect(
        host="mysql.railway.internal",
        user="root",
        password="LMfGYSivOfQiorntcKQEOwBLTqWffTwg",
        database="railway"
        port=3306
    )


# ---------------- PAGES ----------------


@app.route("/get_sessions")
def get_sessions():
    if not os.path.exists(LOG_FILE):
        return jsonify({"sessions": []})

    sessions = []
    current = None

    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()

            if line.startswith("SESSION START"):
                if current:
                    sessions.append(current)

                parts = line.split("|")
                name = parts[1].strip()
                roll = parts[2].strip()

                current = {
                    "name": name,
                    "roll": roll,
                    "events": [],
                    "violations": 0,
                    "status": "RUNNING",
                    "score": "-"
                }

            elif "VIOLATION|" in line and current:
                current["violations"] += 1
                current["events"].append(line)

            elif line.startswith("SESSION END") and current:
                current["status"] = "COMPLETED"
                current["events"].append(line)

                if current["violations"] >= 3:
                    current["status"] = "TERMINATED"

                # extract score if present
                if "Score:" in line:
                    try:
                        score_part = line.split("Score:")[1].split("|")[0].strip()
                        current["score"] = score_part
                    except:
                        pass

                sessions.append(current)
                current = None

            elif current:
                current["events"].append(line)

    return jsonify({"sessions": sessions})

@app.route("/teacher_status", methods=["GET","POST"])
def teacher_status():

    status = None
    reason = None
    message = None

    if request.method == "POST":

        email = request.form["email"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT status, rejection_reason FROM teachers WHERE email=%s",
            (email,)
        )

        teacher = cursor.fetchone()

        cursor.close()
        db.close()

        if teacher:
            status = teacher["status"]
            reason = teacher["rejection_reason"]
        else:
            message = "No teacher application found."

    return render_template(
        "teacher_status.html",
        status=status,
        reason=reason,
        message=message
    )


@app.route('/get_teachers')
def get_teachers():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT name,email,mobile,status FROM teachers")

    teachers = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify({"teachers": teachers})
    

@app.route('/approve_teacher/<email>')
def approve_teacher(email):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE teachers SET status='APPROVED' WHERE email=%s",
        (email,)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({"status":"ok"})


@app.route("/save_exam", methods=["POST"])
def save_exam():

    data = request.json
    questions = data["questions"]

    db = get_db()
    cursor = db.cursor()

    for q in questions:

        question = q["question"]
        qtype = q["type"]

        option1 = option2 = option3 = option4 = None
        answer = q.get("answer","")

        if qtype == "mcq":

            option1 = q["options"][0]
            option2 = q["options"][1]
            option3 = q["options"][2]
            option4 = q["options"][3]

        cursor.execute("""
        INSERT INTO exam_questions
        (question,question_type,option1,option2,option3,option4,correct_answer)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(
            question,
            qtype,
            option1,
            option2,
            option3,
            option4,
            answer
        ))

    db.commit()

    cursor.close()
    db.close()

    return jsonify({"status":"saved"})


@app.route("/get_questions")
def get_questions():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM exam_questions")

    rows = cursor.fetchall()

    questions = []

    for r in rows:

        options = []

        if r["question_type"] == "mcq":
            options = [
                r["option1"],
                r["option2"],
                r["option3"],
                r["option4"]
            ]

        questions.append({
            "question": r["question"],
            "type": r["question_type"],
            "options": options,
            "answer": r["correct_answer"]
        })

    cursor.close()
    db.close()

    return jsonify({"questions": questions})


@app.route('/reject_teacher/<email>', methods=['POST'])
def reject_teacher(email):

    reason = request.json["reason"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE teachers SET status='REJECTED', rejection_reason=%s WHERE email=%s",
        (reason,email)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({"status":"ok"})

@app.route("/teacher_dashboard")
def teacher_dashboard():
    if "teacher" not in session:
        return redirect("/teacher_login")

    return render_template("teacher_dashboard.html")

@app.route("/create_exam")
def create_exam():

    if "teacher" not in session:
        return redirect("/teacher_login")

    return render_template("create_exam.html")


@app.route('/teacher_register', methods=['GET','POST'])
def teacher_register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO teachers (name,email,mobile,status)
            VALUES (%s,%s,%s,'UNDER_REVIEW')
        """,(name,email,mobile))

        db.commit()

        cursor.close()
        db.close()

        return render_template("teacher_register_success.html")

    return render_template('teacher_register.html')


@app.route("/view_result")
def view_result():
    # user must be logged in OR coming from exam
    if session.get("user_id") is None:
        session.clear()
        return redirect(url_for("login_page"))

    session["current_page"] = "view_result"
    return render_template("view_result.html")



@app.route("/teacher_login", methods=["GET","POST"])
def teacher_login():

    if request.method == "POST":

        email = request.form["email"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT status FROM teachers WHERE email=%s",
            (email,)
        )

        teacher = cursor.fetchone()

        cursor.close()
        db.close()

        if teacher and teacher["status"] == "APPROVED":
            session["teacher"] = email
            return redirect("/teacher_dashboard")

        return "Teacher not approved"

    return render_template("teacher_login.html")



@app.route("/api/activity")

def api_activity():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT students.name, exam_results.status
        FROM exam_results
        JOIN students
        ON exam_results.student_id = students.id
        ORDER BY exam_results.exam_date DESC
        LIMIT 5
    """)

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    activities = []

    for r in rows:

        if r["status"] == "COMPLETED":
            activities.append(f'Student {r["name"]} completed exam.')

        elif r["status"] == "PENDING_REVIEW":
            activities.append(f'Student {r["name"]} awaiting evaluation.')

        elif r["status"] == "TERMINATED":
            activities.append(f'Student {r["name"]} exam terminated.')

    return {"activities": activities}


@app.route("/review_exams")
def review_exams():

    if "teacher" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT exam_results.id,
           students.name,
           exam_results.student_id,
           exam_results.score,
           exam_results.total,
           exam_results.status
    FROM exam_results
    JOIN students
    ON exam_results.student_id = students.id
    ORDER BY exam_results.exam_date DESC
""")

    exams = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("review_exams.html", exams=exams)


@app.route("/submit_evaluation", methods=["POST"])
def submit_evaluation():

    result_id = request.form["result_id"]

    total_marks = 0

    for key in request.form:
        if "mark" in key:
            total_marks += int(request.form[key])

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE exam_results
        SET score=%s, status='EVALUATED'
        WHERE id=%s
    """,(total_marks,result_id))

    db.commit()

    cursor.close()
    db.close()

    return redirect("/review_exams")


@app.route("/admin")
def admin_panel():
    return render_template("admin_panel.html")  


@app.route("/maintenance")
def maintenance():
    return render_template("maintenance.html")


@app.route("/")
def homepage():
    return render_template("home.html")

@app.route("/exam_success")
def exam_success():
    return render_template("exam_success.html")

@app.route("/result")
def result_page():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("result.html")


@app.route("/api/result")
def api_result():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT total, score, violations, status, exam_date
            FROM exam_results
            WHERE student_id = %s
            ORDER BY exam_date DESC
            LIMIT 1
        """, (session["user_id"],))

        r = cursor.fetchone()

        cursor.close()
        db.close()

        if not r:
            return jsonify({"empty": True})

        score = r["score"] or 0
        total = r["total"] or 0
        percentage = round((score / total) * 100, 2) if total > 0 else 0

        return jsonify({
            "total": total,
            "score": score,
            "percentage": percentage,
            "violations": r["violations"] or 0,
            "status": r["status"],
            "date": r["exam_date"].strftime("%d %b %Y, %I:%M %p")
        })

    except mysql.connector.Error as e:
        print("❌ API RESULT DB ERROR:", e)
        return jsonify({"error": "database error"}), 500


# @app.route("/")
# def home():
#     return "AI Proctoring Backend is Running"


@app.route("/camera-verify")
def camera_verify():
    if session.get("state") != "logged_in":
        return redirect(url_for("login_page"))
    return render_template("camera_verify.html")



@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard_page():
    if session.get("state") != "logged_in":
        session.clear()
        return redirect(url_for("login_page"))

    # must come from view-result
    if session.get("current_page") != "view_result":
        return redirect(url_for("view_result"))

    session["current_page"] = "dashboard"
    return render_template("dashboard.html", name=session["user_name"])



@app.route("/start_exam", methods=["POST"])
def start_exam():
    if session.get("state") != "logged_in":
        session.clear()
        return jsonify({"status": "unauthorized"}), 401

    session["state"] = "in_exam"
    return jsonify({"status": "ok"})




@app.route("/enter_exam")
def enter_exam():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    # Only dashboard can send here
    if session.get("current_page") != "dashboard":
        return redirect(url_for("dashboard_page"))

    # Allow exam once
    session["current_page"] = "exam"
    return redirect(url_for("exam_page"))


@app.route("/exam")
def exam_page():
    # ❌ Only allowed if exam was started properly
    if session.get("state") != "in_exam":
        session.clear()
        return redirect(url_for("login_page"))

    return render_template("exam.html")





# ---------------- REGISTER API ----------------

@app.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.get_json(silent=True) or request.form
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({
                "status": "error",
                "message": "All fields are required"
            }), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM students WHERE email = %s",
            (email,)
        )

        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()

            return jsonify({
                "status": "error",
                "message": "User already exists. Please login."
            }), 409

        # Insert new user
        hashed_password = generate_password_hash(password)

        cursor.execute(
             "INSERT INTO students (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
                

        db.commit()
        cursor.close()
        db.close()

        return jsonify({
            "status": "success",
            "message": "Registration successful"
        }), 201

    except mysql.connector.Error as e:
        print("❌ REGISTER DB ERROR:", e)
        return jsonify({
            "status": "error",
            "message": "Database error"
        }), 500

    except Exception as e:
        print("❌ REGISTER ERROR:", e)
        return jsonify({
            "status": "error",
            "message": "Server error"
        }), 500


# ---------------- LOGIN API ----------------

@app.route("/login", methods=["POST"])
def login_user():

    data = request.get_json()

    email = data.get("email").strip()
    password = data.get("password").strip()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM students WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    db.close()

    if user and user["password"] == password:

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["state"] = "logged_in"

        return jsonify({
            "status": "success",
            "name": user["name"]
        })

    return jsonify({
        "status": "error",
        "message": "Invalid email or password"
    })

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ---------------- ADMIN LOGS ----------------

@app.route("/get_logs", methods=["GET"])
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})

    with open(LOG_FILE, "r") as file:
        logs = file.readlines()

    return jsonify({"logs": logs})

@app.route("/clear_logs", methods=["POST"])
def clear_logs():
    open(LOG_FILE, "w").close()
    return jsonify({"message": "Logs cleared successfully"})

# ---------------- SESSION LOGGING ----------------

@app.route("/start_session", methods=["POST"])
def start_session():
    data = request.json
    name = data.get("name")
    roll = data.get("roll")

    with open(LOG_FILE, "a") as file:
        file.write("\n" + "="*60 + "\n")
        file.write(f"SESSION START | {name} | {roll} | {datetime.now()}\n")
        file.write("="*60 + "\n")

    return jsonify({"message": "Session started"}), 200


@app.route("/submit_exam", methods=["POST"])
def submit_exam():

    data = request.get_json()

    score = int(data.get("score"))
    total = int(data.get("total"))
    violations = int(data.get("violations"))
    answers = data.get("answers")

    answers_text = "|".join([str(a) for a in answers])

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO exam_results
        (student_id,total,score,violations,answers,status)
        VALUES (%s,%s,%s,%s,%s,%s)
    """,(
        session["user_id"],
        total,
        score,
        violations,
        answers_text,
        "PENDING_REVIEW"
    ))

    db.commit()

    cursor.close()
    db.close()

    return jsonify({"status": "saved"})


@app.route("/teacher_results")
def teacher_results():

    # Teacher must be logged in
    if "teacher" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT students.name,
               exam_results.student_id,
               exam_results.score,
               exam_results.total,
               exam_results.violations,
               exam_results.status,
               exam_results.exam_date
        FROM exam_results
        JOIN students
        ON exam_results.student_id = students.id
        ORDER BY exam_results.exam_date DESC
    """)

    results = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("teacher_results.html", results=results)



@app.route("/evaluate_exam/<int:result_id>")
def evaluate_exam(result_id):

    if "teacher" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT students.name, exam_results.*
        FROM exam_results
        JOIN students
        ON exam_results.student_id = students.id
        WHERE exam_results.id = %s
    """, (result_id,))

    exam = cursor.fetchone()

    # IMPORTANT FIX
    if exam is None:
        cursor.close()
        db.close()
        return "Exam record not found"

    # Safe handling of answers
    student_answers = (exam.get("answers") or "").split("|")

    # Load exam questions
    questions = []
    with open("exam_questions.txt", "r") as f:
        for line in f:
            questions.append(line.strip().split("|"))

    cursor.close()
    db.close()

    return render_template(
        "evaluate_exam.html",
        exam=exam,
        questions=questions,
        answers=student_answers
    )



@app.route("/log_event", methods=["POST"])
def log_event_api():
    data = request.get_json()
    event = data.get("event")

    if not event:
        return jsonify({"status": "error"}), 400

    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} | {event}\n")

    return jsonify({"status": "logged"})

@app.route("/get_violation_count")
def get_violation_count():
    count = 0

    if not os.path.exists(LOG_FILE):
        return jsonify({"count": 0})

    with open(LOG_FILE, "r") as f:
        for line in f:
            if "VIOLATION|" in line:
                count += 1

    return jsonify({"count": count})

import subprocess
import sys

@app.route("/start_ai_engine", methods=["POST"])
def start_ai_engine():
    try:
        script_path = os.path.join(BASE_DIR, "..", "ai_models", "proctor_engine.py")
        script_path = os.path.abspath(script_path)

        subprocess.Popen(
            [sys.executable, script_path],
            shell=True
        )

        print("✅ AI Proctoring Engine Launched")
        return jsonify({"status": "started"})

    except Exception as e:
        print("❌ AI Engine Start Failed:", e)
        return jsonify({"status": "error"}), 500



# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
