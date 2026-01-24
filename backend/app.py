from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask import send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = "ai_proctoring_secret_key"
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "activity_log.txt")

# ---------------- DATABASE ----------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="localhost",
        database="ai_proctoring"
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


@app.route("/view_result")
def view_result():
    # user must be logged in OR coming from exam
    if session.get("user_id") is None:
        session.clear()
        return redirect(url_for("login_page"))

    session["current_page"] = "view_result"
    return render_template("view_result.html")



@app.route("/admin")
def admin_panel():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    admin_path = os.path.join(base_dir, "admin_panel")
    return send_from_directory(admin_path, "index.html")


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
        data = request.get_json()
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
                "message": "You are already registered with this email"
            }), 409

        # Insert new user
        cursor.execute(
            "INSERT INTO students (name, email, password) VALUES (%s, %s, %s)",
            (name, email, password)
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
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"status": "error", "message": "Missing credentials"}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM students WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["state"] = "logged_in"

            return jsonify({"status": "success", "name": user["name"]})

        return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except mysql.connector.Error as e:
        print("❌ LOGIN DB ERROR:", e)
        return jsonify({"status": "error", "message": "Database error"}), 500

    except Exception as e:
        print("❌ LOGIN ERROR:", e)
        return jsonify({"status": "error", "message": "Server error"}), 500


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
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}

    score = int(data.get("score") or 0)
    total = int(data.get("total") or 0)
    violations = int(data.get("violations") or 0)

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO exam_results
            (student_id, total, score, violations, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            total,
            score,
            violations,
            "COMPLETED"
        ))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "Exam submitted successfully"})

    except mysql.connector.Error as e:
        print("❌ SUBMIT EXAM DB ERROR:", e)
        return jsonify({"error": "database error"}), 500






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
    app.run(debug=True)

