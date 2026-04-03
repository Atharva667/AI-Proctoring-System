from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask import send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime
import base64

from werkzeug.security import generate_password_hash, check_password_hash

print("🚀 APP STARTING...")

 
# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = "ai_proctoring_secret_key"
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "activity_log.txt")

@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():

    import numpy as np
    import cv2
    from services.ai_proctoring import analyze_frame as analyze_logic

    data = request.json['image']
    encoded = data.split(',')[1]

    img = base64.b64decode(encoded)
    npimg = np.frombuffer(img, dtype=np.uint8)

    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    user_id = request.remote_addr   # track user

    result = analyze_logic(user_id, frame)

    return jsonify(result)


# ---------------- DATABASE ----------------
def get_db():
    try:
        return mysql.connector.connect(
            host=os.environ.get("MYSQLHOST"),
            user=os.environ.get("MYSQLUSER"),
            password=os.environ.get("MYSQLPASSWORD"),
            database=os.environ.get("MYSQLDATABASE"),
            port=int(os.environ.get("MYSQLPORT", 3306))
        )
    except Exception as e:
        print("❌ DATABASE CONNECTION ERROR:", e)
# ---------------- PAGES ----------------


@app.route("/ping")
def ping():
    return "ok"


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
    try:
        data = request.get_json()

        title = data.get("title")
        questions = data.get("questions")

        db = get_db()
        cursor = db.cursor()

        # create exam first
        cursor.execute(
            "INSERT INTO exams (title, created_by) VALUES (%s,%s)",
            (title, session.get("teacher"))
        )

        exam_id = cursor.lastrowid

        for q in questions:

            question = q.get("question")
            qtype = q.get("type")

            option1 = option2 = option3 = option4 = None
            answer = q.get("answer")

            if qtype == "mcq":
                options = q.get("options", [])
                if len(options) > 0: option1 = options[0]
                if len(options) > 1: option2 = options[1]
                if len(options) > 2: option3 = options[2]
                if len(options) > 3: option4 = options[3]

            cursor.execute("""
            INSERT INTO exam_questions
            (exam_id,question,question_type,option1,option2,option3,option4,correct_answer)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,(
                exam_id,
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

    except Exception as e:
        print("SAVE EXAM ERROR:", e)
        return jsonify({"status":"error"}),500
    
    

@app.route("/get_questions")
def get_questions():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # GET LATEST EXAM
        cursor.execute("SELECT id FROM exams ORDER BY id DESC LIMIT 1")
        exam = cursor.fetchone()

        if not exam:
            return jsonify({"questions": []})

        exam_id = exam["id"]

        # GET QUESTIONS
        cursor.execute("""
            SELECT *
            FROM exam_questions
            WHERE exam_id = %s
            ORDER BY id
        """, (exam_id,))

        rows = cursor.fetchall()

        cursor.close()
        db.close()

        # ✅ CORRECT INDENT STARTS HERE
        questions = []

        for r in rows:
            answer_value = r["correct_answer"]

            try:
                answer_value = int(answer_value)
            except:
                answer_value = 0

            questions.append({
                "exam_id": r["exam_id"],
                "question": r["question"],
                "type": r["question_type"],
                "options": [
                    r["option1"],
                    r["option2"],
                    r["option3"],
                    r["option4"]
                ],
                "answer": answer_value
            })

        return jsonify({"questions": questions})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"questions": []})


@app.route("/process_frame", methods=["POST"])
def process_frame():
    return jsonify({
        "violations": {
            "no_face": 0,
            "multiple_faces": 0,
            "movement": 0,
            "camera_block": 0
        }
    })
    
@app.route("/debug_db")
def debug_db():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM exams")
    exams = cursor.fetchall()

    cursor.execute("SELECT * FROM exam_questions")
    questions = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify({
        "exams": exams,
        "questions": questions
    })


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

@app.route("/api/dashboard_stats")
def dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()

    # Total Exams
    cursor.execute("SELECT COUNT(*) FROM exams")
    total_exams = cursor.fetchone()[0]

    # Students Appeared
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM exam_results")
    students = cursor.fetchone()[0]

    # Pending Reviews
    cursor.execute("SELECT COUNT(*) FROM exam_results WHERE status='PENDING_REVIEW'")
    pending = cursor.fetchone()[0]

    # Total Results
    cursor.execute("SELECT COUNT(*) FROM exam_results")
    results = cursor.fetchone()[0]

    conn.close()

    return {
        "total_exams": total_exams,
        "students": students,
        "pending": pending,
        "results": results
    }

@app.route("/create_exam")
def create_exam():

    if "teacher" not in session:
        return redirect("/teacher_login")

    return render_template("create_exam.html")



@app.route("/publish_exam", methods=["POST"])
def publish_exam():

    try:
        if "teacher" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()

        title = data.get("title")
        questions = data.get("exam_questions")

        # 🔥 VALIDATION
        if not questions or len(questions) == 0:
            return jsonify({"error": "Add at least one question"}), 400

        db = get_db()
        cursor = db.cursor()

        # 👉 Insert exam
        cursor.execute("INSERT INTO exams (title) VALUES (%s)", (title,))
        exam_id = cursor.lastrowid

        # 👉 Insert questions
        for q in questions:
            cursor.execute("""
                INSERT INTO questions (exam_id, question, type)
                VALUES (%s, %s, %s)
            """, (exam_id, q["question"], q["type"]))

        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "Exam created successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


import re

def is_strong_password(password):
    return re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$', password)

@app.route('/teacher_register', methods=['GET','POST'])
def teacher_register():

    try:
        if request.method == 'POST':

            name = request.form['name']
            email = request.form['email']
            mobile = request.form['mobile']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # 🔐 PASSWORD VALIDATION
            if not is_strong_password(password):
                return "Password must be strong (8+ chars, uppercase, lowercase, number, special char)", 400

            if password != confirm_password:
                return "Passwords do not match", 400

            db = get_db()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO teachers (name,email,mobile,password,status)
                VALUES (%s,%s,%s,%s,'UNDER_REVIEW')
            """,(name,email,mobile,password))

            db.commit()

            cursor.close()
            db.close()

            return render_template("teacher_register_success.html")

        return render_template('teacher_register.html')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return str(e)

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

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
    SELECT 
        s.id as student_id,
        s.name,
        COUNT(er.id) as attempts,
        MAX(CAST(er.score AS SIGNED)) as best_score,
        MAX(er.total) as total,
        MAX(er.id) as latest_id,
        MAX(CASE WHEN er.status='PENDING_REVIEW' THEN er.id ELSE NULL END) as pending_id,
        SUM(CASE WHEN er.status='PENDING_REVIEW' THEN 1 ELSE 0 END) as pending_count
    FROM exam_results er
    JOIN students s ON er.student_id = s.id
    GROUP BY s.id, s.name
    ORDER BY MAX(er.id) DESC
""")   
        exams = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template("review_exams.html", exams=exams)

    except Exception as e:
        print("REVIEW_EXAMS ERROR:", e)
        return "Server error loading exams"
    
@app.route("/student_attempts/<int:student_id>")
def student_attempts(student_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM exam_results
        WHERE student_id = %s
        ORDER BY id DESC
    """, (student_id,))

    attempts = cursor.fetchall()

    return render_template("student_attempts.html", attempts=attempts)



# @app.route("/review_exams_latest")
# def review_exams_latest():

#     if "teacher" not in session:
#         return redirect("/teacher_login")

#     try:
#         db = get_db()
#         cursor = db.cursor(dictionary=True)

#         cursor.execute("""
#         SELECT er.id, s.name, er.total, er.score, er.status
#         FROM exam_results er
#         JOIN (
#             SELECT student_id, MAX(id) as latest_id
#             FROM exam_results
#             GROUP BY student_id
#         ) latest
#         ON er.id = latest.latest_id
#         JOIN students s ON er.student_id = s.id
#         ORDER BY er.id DESC
#         """)

#         exams = cursor.fetchall()

#         cursor.close()
#         db.close()

#         return render_template("review_exams.html", exams=exams)

#     except Exception as e:
#         print("LATEST ERROR:", e)
#         return "Error"


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

    if session.get("admin") != True:
        return redirect("/admin_login")

    return render_template("admin_panel.html")

@app.route("/maintenance")
def maintenance():
    return render_template("maintenance.html")

# ---------------- ADMIN LOGIN ----------------

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin"] = True
            return redirect("/admin")

        else:
            return render_template(
                "admin_login.html",
                error="Invalid admin credentials"
            )

    return render_template("admin_login.html")


from flask import request, jsonify, session
from werkzeug.security import generate_password_hash
import mysql.connector

@app.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.get_json(silent=True) or request.form

        name = data.get("name")
        login = data.get("login")   # email or phone
        password = data.get("password")

        # ================= VALIDATION =================
        if not name or not login or not password:
            return jsonify({
                "status": "error",
                "message": "All fields are required"
            }), 400

 

        # ================= DETECT EMAIL / PHONE =================
        if "@" in login:
            email = login
            mobile = None
        else:
            email = None
            mobile = login

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # ================= CHECK EXISTING USER =================
        cursor.execute("""
            SELECT id FROM students 
            WHERE email = %s OR mobile = %s
        """, (email, mobile))

        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()

            return jsonify({
                "status": "error",
                "message": "User already exists. Please login."
            }), 409

        # ================= HASH PASSWORD =================
        hashed_password = generate_password_hash(password)

        # ================= INSERT USER =================
        cursor.execute("""
            INSERT INTO students (name, email, mobile, password) 
            VALUES (%s, %s, %s, %s)
        """, (name, email, mobile, hashed_password))

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
    



@app.route("/admin_logout")
def admin_logout():

    session.pop("admin", None)

    return redirect("/admin_login")


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


@app.route('/api/result')
def api_result():

    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    student_id = session["user_id"]   # ⭐ ADD THIS LINE

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM exam_results
            WHERE student_id=%s
            ORDER BY id DESC
            LIMIT 1
        """,(student_id,))

        r = cursor.fetchone()

        cursor.close()
        db.close()

        if not r:
            return jsonify({"empty": True})

        total = r.get("total") or 0
        score = r.get("score") or 0
        violations = r.get("violations") or 0
        status = r.get("status") or "UNKNOWN"

        percentage = 0
        if total > 0:
            percentage = round((score / total) * 100, 2)

        # Safe date handling
        date = ""
        if r.get("exam_date"):
            try:
                date = r["exam_date"].strftime("%d %b %Y, %I:%M %p")
            except:
                date = str(r["exam_date"])

        return jsonify({
            "total": total,
            "score": score,
            "percentage": percentage,
            "violations": violations,
            "status": status,
            "date": date
        })

    except Exception as e:

        print("API RESULT ERROR:", e)

        return jsonify({
            "error": "server_error"
        }), 500


@app.route("/camera-verify")
def camera_verify():

    if session.get("state") != "logged_in":
        return redirect(url_for("login_page"))

    # ✅ IMPORTANT FIX
    session["verified"] = True
    session.modified = True

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

    # ✅ Check login
    if not session.get("user_id"):
        session.clear()
        return jsonify({"status": "unauthorized"}), 401

    student_id = session.get("user_id")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 🔥 GET CURRENT EXAM (LATEST)
    cursor.execute("SELECT id FROM exams ORDER BY id DESC LIMIT 1")
    exam = cursor.fetchone()

    if not exam:
        cursor.close()
        db.close()
        return jsonify({"status": "no_exam"})

    exam_id = exam["id"]

    # 🔥 CHECK IF STUDENT ALREADY ATTEMPTED THIS EXAM
    cursor.execute("""
        SELECT id FROM exam_results
        WHERE student_id = %s AND exam_id = %s
        LIMIT 1
    """, (student_id, exam_id))

    already_attempted = cursor.fetchone()

    cursor.close()
    db.close()

    # ❌ BLOCK IF ALREADY ATTEMPTED
    if already_attempted:
        return jsonify({
            "status": "blocked",
            "message": "You have already attempted this exam"
        })

    # ✅ ALLOW EXAM
    session["state"] = "in_exam"
    session["exam_id"] = exam_id
    session.modified = True

    print("SESSION STARTED:", dict(session))

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

    if not session.get("user_id"):
        session.clear()
        return redirect(url_for("login_page"))

    return render_template("exam.html")




 

# ---------------- LOGIN API ----------------
from flask import request, jsonify, session
from werkzeug.security import check_password_hash

@app.route("/login", methods=["POST"])
def login_user():

    data = request.get_json(silent=True) or request.form

    login_input = data.get("login", "").strip()
    password = data.get("password", "").strip()

    if not login_input or not password:
        return jsonify({
            "status": "error",
            "message": "Please enter email/phone and password"
        })

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 🔥 MAIN CHANGE (EMAIL OR PHONE)
    cursor.execute("""
        SELECT * FROM students
        WHERE email=%s OR mobile=%s
    """, (login_input, login_input))

    user = cursor.fetchone()

    cursor.close()
    db.close()

    if user and check_password_hash(user["password"], password):

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["state"] = "logged_in"

        return jsonify({
            "status": "success",
            "name": user["name"]
        })

    return jsonify({
        "status": "error",
        "message": "Invalid email/phone or password"
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
    try:
        data = request.get_json()

        exam_id = int(data.get("exam_id"))
        score = int(data.get("score"))
        total = int(data.get("total"))
        violations = int(data.get("violations"))
        answers = data.get("answers")

        answers_text = "|".join([str(a) for a in answers])
        student_id = session.get("user_id")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # 🔥 CHECK IF DESCRIPTIVE EXISTS
        cursor.execute("""
            SELECT question_type FROM exam_questions WHERE exam_id=%s
        """, (exam_id,))

        questions = cursor.fetchall()

        needs_review = any(q["question_type"] in ["short","paragraph"] for q in questions)

        if needs_review:
            status = "PARTIAL_EVALUATED"
        else:
            status = "EVALUATED"

        cursor = db.cursor()

        cursor.execute("""
        INSERT INTO exam_results
        (student_id, exam_id, total, score, violations, answers, status, exam_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
        """,(
            student_id,
            exam_id,
            total,
            score,
            violations,
            answers_text,
            status
        ))

        db.commit()

        cursor.close()
        db.close()

        return jsonify({"status": "saved"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status":"error"})


@app.route("/teacher_results")
def teacher_results():

    if "teacher" not in session:
        return redirect("/teacher_login")

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
SELECT
s.name,
er.total,
er.score,
CASE 
WHEN er.total > 0 THEN ROUND((er.score/er.total)*100,2)
ELSE 0 
END AS percentage,
er.violations,
er.status
FROM exam_results er
JOIN students s ON er.student_id = s.id
ORDER BY er.id DESC
""")

        results = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template("teacher_results.html", results=results)

    except Exception as e:
        print("TEACHER_RESULTS ERROR:", e)
        return "Server error loading teacher results"




@app.route("/evaluate_exam/<int:result_id>")
def evaluate_exam(result_id):

    if "teacher" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ✅ GET RESULT
    cursor.execute("""
    SELECT er.*, s.name
    FROM exam_results er
    JOIN students s ON er.student_id = s.id
    WHERE er.id=%s
""", (result_id,))

    result = cursor.fetchone()

    if not result:
        return "Exam record not found"

    exam_id = result["exam_id"]

    # ❌ THIS WAS YOUR BUG → exam_id mismatch earlier
    if not exam_id:
        return "Exam ID missing"

    # ✅ GET QUESTIONS
    cursor.execute("""
        SELECT *
        FROM exam_questions
        WHERE exam_id=%s
        ORDER BY id
    """, (exam_id,))

    questions = cursor.fetchall()

    # ✅ GET ANSWERS
    answers = (result["answers"] or "").split("|")

    cursor.close()
    db.close()

    return render_template(
        "evaluate_exam.html",
        questions=questions,
        exam=result,
        answers=answers,
        result_id=result_id
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)